# Contract Clause Reviewer — Frontend

React 19 + TypeScript single-page application that consumes the FastAPI backend.

For the full architecture, state ownership, and design decisions, see [`../docs/frontend.md`](../docs/frontend.md).

---

## Requirements

- Node.js 20+
- pnpm 9+

---

## Quick Start

```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

The frontend is exposed on `http://localhost:5173`.

The backend must be running on `http://localhost:9000` (default) for the API proxy to work. See the root [`README.md`](../README.md) for backend setup.

---

## Environment Variables

Only one variable is required:

```bash
# frontend/.env
VITE_API_BASE_URL=
```

**Leave it empty for local development.** Vite's dev server proxies `/api/*` requests to `http://localhost:9000` (or the value of `VITE_API_BASE_URL` if set as the proxy target — see `vite.config.ts`).

For production, set `VITE_API_BASE_URL` to the API origin if the frontend and backend are served from different origins:

```bash
VITE_API_BASE_URL=https://api.example.com
```

If frontend and backend share an origin (recommended, via reverse proxy), leave it empty and configure the proxy to route `/api/*` to the backend.

---

## Commands

| Command          | Description                                    |
| ---------------- | ---------------------------------------------- |
| `pnpm dev`       | Start Vite dev server with HMR                 |
| `pnpm build`     | TypeScript check + production build to `dist/` |
| `pnpm preview`   | Preview the production build locally           |
| `pnpm lint`      | Run ESLint                                     |
| `pnpm lint:fix`  | ESLint + Prettier auto-fix                     |
| `pnpm format`    | Prettier format                                |
| `pnpm typecheck` | TypeScript check without emitting              |
| `pnpm test`      | Run Vitest in watch mode                       |
| `pnpm test:run`  | Run Vitest once (CI)                           |
| `pnpm coverage`  | Generate coverage report                       |

---

## Directory Structure

```text
src/
├── app/                    # Root composition (providers)
│   └── providers.tsx       # ThemeProvider, AuthProvider, QueryClientProvider
├── components/
│   ├── ui/                 # shadcn primitives
│   ├── layout/             # app-shell, header, nav, sidebar, public-layout
│   └── common/             # EmptyState, PageHeader
├── features/               # Feature slices (mirror backend API tags)
│   ├── auth/
│   │   ├── api.ts
│   │   ├── schemas.ts
│   │   └── components/     # protected-route, require-role
│   ├── analysis/
│   │   ├── api.ts
│   │   ├── schemas.ts
│   │   ├── hooks.ts        # useAnalysisStatus
│   │   ├── analysis-form.tsx
│   │   └── components/
│   ├── reports/
│   │   ├── api.ts
│   │   ├── hooks.ts        # useReportStatus
│   │   └── components/     # report-widget
│   └── users/
│       ├── api.ts
│       ├── schemas.ts
│       ├── hooks.ts        # useUsersList
│       └── components/     # forms, dialogs, table, filters, pagination
├── hooks/                  # Generic hooks (use-debounce)
├── lib/
│   ├── api/                # API client, errors, auth interceptor, error-message
│   ├── auth/               # auth-context, auth-provider, storage, tokens, hooks, guest-route
│   ├── forms/              # handle-form-error
│   └── utils.ts            # cn()
├── pages/                  # Route-level components
│   ├── admin/
│   ├── analysis/
│   ├── auth/
│   ├── dashboard/
│   ├── profile/
│   └── not-found-page.tsx
├── styles/                 # globals.css (Tailwind + theme CSS vars)
├── tests/                  # Shared test infrastructure
│   ├── setup.ts
│   ├── test-utils.tsx      # renderWithProviders, renderHookWithProviders
│   ├── auth-mocks.ts       # mockAuthState + helpers
│   └── integration/        # Cross-feature integration tests
├── types/                  # API contracts mirroring backend Pydantic schemas
├── router.tsx              # Route table with guards
├── App.tsx                 # Root component (renders Router)
└── main.tsx                # Vite entry point
```

---

## Conventions

- **Feature-first organization.** Everything related to analysis lives in `features/analysis/`. Features don't import from other features.
- **Types vs. schemas.** `src/types/` holds pure TS interfaces mirroring the backend wire format. `src/features/*/schemas.ts` holds Zod schemas for runtime form validation. They serve different purposes and must not be merged.
- **One API client.** Feature files call API functions; API functions call `apiClient`. Never call `fetch` directly except for binary downloads.
- **Query keys.** Follow `[resource, ...params]`. Prefix-match invalidation depends on this shape.
- **Mutation keys.** Follow `[resource, action, optional-id]`. Required for DevTools visibility.
- **Form mode.** `mode: "onChange"` when the submit button depends on `isValid`. `mode: "onTouched"` when it doesn't.
- **Shared styles.** Use `cn()` from `@/lib/utils` for conditional classes. Never use template strings.

---

## Testing

Setup details in `vitest.config.ts` and `src/tests/setup.ts`. Tests co-locate with the source:

```text
src/lib/api/client.test.ts          ← next to client.ts
src/pages/auth/login-page.test.tsx  ← next to login-page.tsx
```

Shared infrastructure lives in `src/tests/`:

- `setup.ts` — loads `@testing-library/jest-dom`, runs `cleanup()` after each test.
- `test-utils.tsx` — `renderWithProviders`, `renderHookWithProviders` (wrap in `QueryClientProvider` + `MemoryRouter`).
- `auth-mocks.ts` — `mockAuthState`, `mockAuthenticated`, `mockUnauthenticated` for `useAuth` mocking.

```bash
pnpm test              # watch mode
pnpm test:run          # one-shot
pnpm test src/lib/api  # filter by path
pnpm coverage          # coverage report
```

Conventions:

- Use `getByRole`, `getByLabelText`, `getByText`. `getByTestId` is last resort.
- Use `userEvent.setup()` and `await` its methods. Never `fireEvent` unless necessary.
- Use `{ exact: true }` with `getByLabelText` when labels overlap (e.g., "Password" vs. "Confirm New Password").
- Mock at the API module boundary (`vi.mock("./api")`), not `fetch`.
- Mock `useAuth` via `mockAuthState` — do not wrap in the real `AuthProvider` except when testing auth lifecycle.
- Mock TanStack Query mutations with `expect.anything()` as the second argument (TanStack Query v5 passes context to `mutationFn`).

---

## Building for Production

```bash
pnpm build
```

Outputs to `frontend/dist/`:

- `index.html`
- `assets/*.js` — hashed JS bundles
- `assets/*.css` — hashed CSS
- `assets/*.woff2` — self-hosted fonts

The `dist/` directory contains only static assets. Serve it with any HTTP server:

- **Nginx/Caddy** — recommended for production. Configure a fallback route (`try_files $uri /index.html`) for React Router's client-side routes. Proxy `/api/*` to the FastAPI backend.
- **Static host (Vercel/Netlify/Cloudflare Pages)** — deploy `dist/` and configure the same fallback + an API proxy or CORS policy.
- **FastAPI StaticFiles** — mount `frontend/dist/` as a StaticFiles route on the backend (small projects only; adds build coupling).

The frontend does not require Node.js at runtime. Once built, it's plain HTML/CSS/JS.

---

## Known Limitations

See [`../docs/frontend.md#known-limitations`](../docs/frontend.md#known-limitations).

The most important ones:

- Filters on the users list are not URL-encoded — refresh loses them.
- No optimistic updates on mutations (refetch after success).
- No SSR — this is a pure SPA.
- Report generation polling dies if the user navigates away (they must click "Generate Report" again on return; the backend recognizes the existing report and offers it for download).
