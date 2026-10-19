# React Frontend Architecture

The `frontend/` directory contains a React 19 + TypeScript single-page application that consumes the FastAPI backend as a pure API client. This document describes the architecture, state ownership, and key decisions. For local development, see [`frontend/README.md`](../frontend/README.md).

---

## Design principles

1. **Feature-oriented architecture.** Code is organized by business capability (`auth`, `users`, `analysis`, `reports`), mirroring the backend's API tag structure. Each feature slice contains its own API module, schemas, hooks, and components.
2. **One owner per concern.** Server state belongs to TanStack Query. Form state belongs to React Hook Form. Session state belongs to React Context. UI state belongs to local `useState`. Nothing overlaps.
3. **The API client is a boundary, not a utility.** Feature files call API functions; API functions call the client; the client handles HTTP concerns. Feature code never imports `fetch`.
4. **Framework boundaries over clever abstractions.** No Redux, no Zustand, no global stores. TanStack Query's cache is the server-state store; React Context is the session store. Both are library-provided, not hand-rolled.
5. **Route guards are UX.** `RequireAuth` and `RequireRole` improve user experience. The backend remains the security boundary — every protected endpoint is enforced server-side.

---

## Layers

```text
pages/          route-level components (thin composition)
   ↓
features/       vertical slices: api.ts, schemas.ts, hooks.ts, components/
   ↓
components/     reusable UI (ui/, layout/, common/)
   ↓
lib/            infrastructure: API client, auth storage, tokens, forms
   ↓
types/          shared TypeScript contracts mirroring backend Pydantic schemas
```

**Pages** — Read a URL param, validate it, and hand off to feature components. A page does not fetch; it composes. Example: `analysis-detail-page.tsx` reads `analysisId`, validates it, and renders `<AnalysisDetailView>`, `<ReportWidget>`, and the clause cards.

**Features** — One folder per backend API tag. `features/analysis/` owns `api.ts` (calls `apiClient`), `schemas.ts` (Zod for form input), `hooks.ts` (polling, list), and `components/` (form, result view, cards). Features do not import from other features — only from `lib/`, `components/`, and `types/`.

**Components** — Three subfolders:

- `ui/` — shadcn primitives (Button, Input, Card, Dialog, Table...)
- `layout/` — app shell, sidebar, header, mobile nav
- `common/` — app-aware patterns (EmptyState, PageHeader)

**lib/** — Infrastructure that does not import React. The API client, error types, auth storage, JWT helpers, and form error handler. Testable without rendering anything.

**types/** — Pure TypeScript interfaces mirroring the backend OpenAPI schemas. Zero runtime cost, single source of truth for wire formats.

---

## State ownership

The project deliberately splits state by **where it comes from**:

| State                 | Owner                              | Example                                   |
| --------------------- | ---------------------------------- | ----------------------------------------- |
| Server data (fetched) | TanStack Query                     | Users list, current user, analysis detail |
| Server data (polled)  | TanStack Query + `refetchInterval` | Analysis status, report status            |
| Form field values     | React Hook Form                    | Login, analysis form, password change     |
| Form validation       | Zod schemas                        | Every form                                |
| Auth session          | React Context                      | `{ user, status, login, logout }`         |
| UI state              | Local `useState`                   | Dialog open, filter values, mobile nav    |
| Toast/alert feedback  | Local `useState`                   | Form submit success/error                 |

**No state is duplicated.** The classic bug — a header showing a stale username because the profile page updated context and not the query cache — is avoided by having `updateUser` in the auth context called by mutations that affect the user, alongside `invalidateQueries(["current-user"])`.

---

## Query key conventions

All query keys follow `[resource, ...params]`:

```ts
["analysis-detail", analysisId][("analysis-status", taskId)][
  ("analysis-list", params)
][("report-status", taskId)][("users-list", params)][("user-detail", userId)][
  "current-user"
]; // shared between profile and dashboard
```

**Why the shape matters:** `invalidateQueries({ queryKey: ["users-list"] })` invalidates every variant (every page, every filter) by prefix match. If keys were `["users"]` in one place and `["users-list"]` in another, invalidation would miss half the cache.

**Shared keys mean shared cache.** Profile and dashboard both use `["current-user"]`. Whichever page loads first triggers the fetch; the other reuses the result. When a username is updated, the mutation invalidates `["current-user"]`, and both pages refetch.

---

## Mutation key conventions

All mutation keys follow `[resource, action, optional-id]`:

```ts
["auth", "login"][("analysis", "submit")][("users", "create")][
  ("users", "update", userId)
][("users", "delete", userId)][("profile", "update-username")][
  ("profile", "change-password")
][("reports", "generate", analysisId)][("reports", "download", analysisId)];
```

Mutation keys do not affect caching (mutations don't cache). They exist for DevTools visibility and for identifying in-flight mutations. Always provide one — without it, the mutation appears anonymous in the DevTools panel.

---

## API client

`src/lib/api/client.ts` is the single HTTP boundary. It wraps `fetch` and handles:

- Base URL composition (from `VITE_API_BASE_URL`, empty in dev for proxy)
- Query param serialization, including arrays as repeated keys (FastAPI convention)
- JSON body serialization
- `Accept` and `Content-Type` headers
- Bearer token attachment from `tokenStorage` (or the injected `AuthHandler`)
- Response parsing — 204 returns `undefined`, otherwise JSON
- Error normalization — FastAPI 422 arrays and string `detail` both become `HttpError`
- Network error wrapping — `fetch` failures become `NetworkError`
- **401 handling** — a single-flight refresh queue retries the original request after refresh; concurrent 401s wait on the same refresh promise

Feature modules call `api.get<T>()`, `api.post<T>()`, `api.patch<T>()`, `api.delete<T>()`. They never call `fetch` directly.

**The one exception** is `downloadReport` in `features/reports/api.ts` — the PDF endpoint returns binary data, not JSON. It uses `fetch` directly with the bearer token and returns a `Blob`. This is documented and localized.

---

## Auth lifecycle

`AuthProvider` (`src/lib/auth/auth-provider.tsx`) owns the session:

- **On mount**: reads tokens from `localStorage`. If present, calls `/users/me`. If that 401s, attempts a refresh, then retries `/users/me`. If anything fails, clears tokens and marks unauthenticated.
- **On login**: calls `/auth/login`, stores tokens, fetches `/users/me`, marks authenticated.
- **On logout**: calls `/auth/logout`, clears tokens, resets `user` and `status`, and **clears the entire query cache** (`queryClient.clear()`) to prevent cross-user data leaks.
- **On 401 from any endpoint**: the API client's interceptor fires the refresh queue. If refresh succeeds, it retries; if it fails, it invokes `logout()`.

The `AuthHandler` object — `{ getToken, refreshToken, logout }` — is injected into the API client via `setAuthHandler`. This keeps `lib/api/` free of React context dependencies.

**On the JWT payload:** the backend places the user's UUID in `sub`, not the username. This means a username change does not invalidate existing access tokens — the tokens still identify the same user. The frontend syncs the display name via `updateUser` on the auth context after the username mutation succeeds.

---

## Routing and route guards

`router.tsx` defines the tree:

```text
/                         → redirect to /dashboard
/login                    → <GuestRoute>
/dashboard                → <RequireAuth> + <AppShell>
/analysis/new             → <RequireAuth>
/analysis/status/:taskId  → <RequireAuth>
/analysis/:analysisId     → <RequireAuth>
/reports/:analysisId      → <RequireAuth>
/profile                  → <RequireAuth>
/admin/users              → <RequireRole allowedRoles={["admin"]}>
*                         → <NotFoundPage>
```

Guards:

- **`RequireAuth`** — if status is `initializing`, shows a full-page spinner. If `unauthenticated`, redirects to `/login` with `state.from` so the user lands back where they came from after signing in.
- **`RequireRole`** — reads `user.role` and redirects to `/dashboard` if not in the allowed list. Also renders nothing if the user isn't loaded yet.
- **`GuestRoute`** — redirects authenticated users away from `/login` to their intended destination.

---

## Forms

Every form uses the same stack:

- **React Hook Form** for field state
- **Zod** for schema validation via `@hookform/resolvers/zod`
- **shadcn `Field` primitives** for accessible labels, descriptions, and error display
- **`handleFormError`** for server error mapping

The shared `handleFormError` (`src/lib/forms/handle-form-error.ts`) maps FastAPI 422 arrays to `form.setError` calls and falls back to a form-level error message for string `detail` responses. It takes an optional `fieldMap` to translate backend snake_case fields (`old_password`) to form field names (`oldPassword`).

**Form modes:** most forms use `mode: "onChange"` because they gate the submit button on `formState.isValid` — instant validation is required for the button to enable reliably. The analysis form uses `mode: "onTouched"` because its submit button is not gated on `isValid` and the "quiet until blur" UX suits a long-form input.

**Optional fields** (like `description` on the analysis form) use `value={field.value ?? ""}` to satisfy controlled-input requirements, and a Zod `.transform()` to normalize empty strings to `undefined` before submission.

---

## Polling

Two hooks poll long-running tasks:

- `useAnalysisStatus(taskId)` — polls `/analysis/status/{taskId}` every 5s
- `useReportStatus(taskId)` — polls `/reports/status/{taskId}` every 2s

Both are implemented via TanStack Query's `refetchInterval`:

```ts
useQuery({
  queryKey: ["analysis-status", taskId],
  queryFn: () => getAnalysisStatus(taskId!),
  enabled: Boolean(taskId),
  retry: false,
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    if (status === "completed" || status === "failed") return false;
    if ((query.state.fetchFailureCount ?? 0) >= 3) return false;
    return 5000;
  },
});
```

**The pattern:**

- `enabled` prevents the query from running before a `taskId` exists.
- `retry: false` makes `fetchFailureCount` count polls, not retries.
- `refetchInterval` returns a number to keep polling or `false` to stop.
- Terminal states (`completed`, `failed`) stop the loop.
- Three consecutive failures stop the loop so a broken backend isn't hammered.

`useAnalysisStatus` redirects to `/analysis/{id}` on completion (via a side effect in `AnalysisStatusPage`). `useReportStatus` does not navigate — it exposes the completed status to `ReportWidget`, which renders the download button in place.

---

## File download

`downloadReport(analysisId)` returns a `Blob` via native `fetch` (the one exception to the "use the client" rule). `ReportWidget` triggers the browser download via `URL.createObjectURL` + a temp anchor element + `URL.revokeObjectURL`.

The bearer token is attached manually in `downloadReport` because the standard client is not used for this call.

---

## Testing

The frontend test suite uses **Vitest + React Testing Library + jsdom**. See [`frontend/README.md`](../frontend/README.md#testing) for setup, and the skills notes in the project root for conventions.

Coverage focuses on:

- **Pure logic** — API client (`client.test.ts`, `errors.test.ts`, `auth-interceptor.test.ts`, `error-message.test.ts`), auth tokens (`tokens.test.ts`), storage (`storage.test.ts`), form error mapping (`handle-form-error.test.ts`), debounce (`use-debounce.test.ts`)
- **Route guards** — `protected-route.test.tsx`, `require-role.test.tsx`
- **Form validation** — `password-form.test.tsx`, `analysis-form.test.tsx`
- **Critical flows** — `login-page.test.tsx`, `auth-flow.test.tsx` (session restoration, logout cache clearing)
- **TanStack Query hooks** — `reports/hooks.test.ts` (polling terminal behavior)

**What is not tested:** shadcn primitives (tested by the library), CSS classes (break on theme change), internal state (couples to implementation), and hooks used only in one component (test the component instead).

---

## Known limitations

- **Filters are not URL-encoded.** Users page pagination and filters live in local state — refreshing loses them. Promoting to `useSearchParams` is a future improvement.
- **No optimistic updates.** Mutations invalidate their affected queries and wait for a refetch. This is correct but slightly slower than optimistic updates, which are deferred until the tradeoff justifies the complexity.
- **No SSR.** The frontend is a pure SPA. Pages that need crawling (marketing pages, public docs) would need a Next.js or Astro port.
- **Report widget loses polling on navigation.** If a user starts report generation and leaves the analysis detail page, the poll dies. They'd need to click "Generate Report" again on return (which the backend recognizes and downloads the existing report). For short tasks this is acceptable.
- **No shared frontend/backend deployment.** Currently the frontend runs on Vite's dev server against the backend on port 9000. A production deployment behind a reverse proxy (Nginx/Caddy serving `frontend/dist` and proxying `/api/*` to FastAPI) is documented but not yet scripted.
