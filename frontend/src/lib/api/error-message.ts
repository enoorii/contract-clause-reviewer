import { HttpError, NetworkError } from "./types";

export function getErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpError || err instanceof NetworkError) {
    return err.message;
  }
  return fallback;
}
