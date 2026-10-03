// src/features/users/components/username-form.tsx
import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import { usernameUpdateSchema, type UsernameUpdateInput } from "../schemas";
import { updateProfile } from "../api";
import { HttpError, NetworkError } from "@/lib/api/types";

import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

/**
 * Discriminated union for the outcome of a submit attempt.
 * Note: deliberately omits "submitting" — RHF owns that via formState.
 */
type SubmitFeedback =
  | { kind: "idle" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

interface UsernameFormProps {
  initialUsername: string;
  onSuccess?: (newUsername: string) => void;
}

export function UsernameForm({
  initialUsername,
  onSuccess,
}: UsernameFormProps) {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  const form = useForm<UsernameUpdateInput>({
    mode: "onChange",
    resolver: zodResolver(usernameUpdateSchema),
    defaultValues: { username: initialUsername },
  });

  async function onSubmit(data: UsernameUpdateInput) {
    setFeedback({ kind: "idle" });

    try {
      const updated = await updateProfile(data.username);
      // Reset with the server's canonical value — in case the backend
      // normalizes it (trimming, casing, etc.).
      form.reset({ username: updated.username });
      setFeedback({ kind: "success", message: "Username updated." });
      onSuccess?.(updated.username);
    } catch (error: unknown) {
      if (error instanceof HttpError) {
        const details = error.details;

        // 422: FastAPI validation errors — map to form fields.
        // The backend reports the field as "new_username" (query param name),
        // so we accept both that and "username".
        if (error.status === 422 && Array.isArray(details)) {
          for (const err of details) {
            const rawField = err.loc[err.loc.length - 1];
            if (rawField === "new_username" || rawField === "username") {
              form.setError("username", { type: "server", message: err.msg });
            } else {
              setFeedback({ kind: "error", message: err.msg });
            }
          }
          return;
        }

        if (typeof details === "string") {
          setFeedback({ kind: "error", message: details });
          return;
        }

        setFeedback({
          kind: "error",
          message: error.message || "Failed to update username.",
        });
        return;
      }

      setFeedback({
        kind: "error",
        message:
          error instanceof NetworkError
            ? error.message
            : "An unexpected error occurred.",
      });
    }
  }

  const { isSubmitting, isValid, isDirty } = form.formState;

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {feedback.kind === "success" && !isDirty && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{feedback.message}</AlertDescription>
        </Alert>
      )}

      {feedback.kind === "error" && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{feedback.message}</AlertDescription>
        </Alert>
      )}

      <Controller
        control={form.control}
        name="username"
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor={field.name}>Username</FieldLabel>
            <Input
              id={field.name}
              placeholder="your-username"
              autoComplete="username"
              aria-invalid={fieldState.invalid}
              {...field}
            />
            <FieldDescription>
              At least 3 characters. Used to log in.
            </FieldDescription>
            {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
          </Field>
        )}
      />

      <Button type="submit" disabled={isSubmitting || !isValid || !isDirty}>
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving...
          </>
        ) : (
          "Save Changes"
        )}
      </Button>
    </form>
  );
}
