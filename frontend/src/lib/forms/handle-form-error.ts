import type { UseFormReturn, FieldValues, Path } from "react-hook-form";
import { HttpError, NetworkError } from "@/lib/api/types";

interface HandleFormErrorOptions<T extends FieldValues> {
  form: UseFormReturn<T>;
  /** Map backend field names → form field names (e.g., "old_password" → "oldPassword") */
  fieldMap?: Record<string, Path<T>>;
  /** Called for errors that don't map to a field */
  setFormError: (message: string) => void;
  /** Fallback when the error is untyped */
  fallback: string;
}

export function handleFormError<T extends FieldValues>(
  err: unknown,
  { form, fieldMap = {}, setFormError, fallback }: HandleFormErrorOptions<T>,
): void {
  if (!(err instanceof HttpError)) {
    setFormError(
      err instanceof NetworkError
        ? err.message
        : "An unexpected error occurred.",
    );
    return;
  }

  const details = err.details;

  if (err.status === 422 && Array.isArray(details)) {
    for (const e of details) {
      const raw = String(e.loc[e.loc.length - 1]);
      const formField = fieldMap[raw] ?? raw;
      if (formField in form.getValues()) {
        form.setError(formField as Path<T>, { type: "server", message: e.msg });
      } else {
        setFormError(e.msg);
      }
    }
    return;
  }

  if (typeof details === "string") {
    setFormError(details);
    return;
  }

  setFormError(err.message || fallback);
}
