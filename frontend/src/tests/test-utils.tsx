// src/test/test-utils.tsx
import type { ReactElement, ReactNode } from "react";
import {
  render,
  renderHook,
  type RenderOptions,
  type RenderHookOptions,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}

interface WrapperProps {
  children: ReactNode;
  initialEntries: string[];
}

function Providers({ children, initialEntries }: WrapperProps) {
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  initialEntries?: string[];
}

export function renderWithProviders(
  ui: ReactElement,
  { initialEntries = ["/"], ...options }: CustomRenderOptions = {},
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <Providers initialEntries={initialEntries}>{children}</Providers>
    ),
    ...options,
  });
}

interface CustomRenderHookOptions<Props> extends Omit<
  RenderHookOptions<Props>,
  "wrapper"
> {
  initialEntries?: string[];
}

export function renderHookWithProviders<Result, Props>(
  callback: (initialProps: Props) => Result,
  { initialEntries = ["/"], ...options }: CustomRenderHookOptions<Props> = {},
) {
  return renderHook(callback, {
    wrapper: ({ children }) => (
      <Providers initialEntries={initialEntries}>{children}</Providers>
    ),
    ...options,
  });
}

// Do not use `export *` here — re-export only the pieces test files need.
export { screen, waitFor, within, fireEvent } from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
