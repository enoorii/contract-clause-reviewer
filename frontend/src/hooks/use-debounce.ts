// src/hooks/use-debounce.ts
import { useEffect, useState } from "react";

/**
 * Delays propagating a value until `delayMs` has passed without further
 * changes. Use for search inputs where you don't want to fire a request
 * on every keystroke.
 *
 * The returned value lags behind the input by up to `delayMs`. Typing
 * "alice" with a 300ms debounce fires one fetch after the user pauses,
 * rather than five fetches.
 */
export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
