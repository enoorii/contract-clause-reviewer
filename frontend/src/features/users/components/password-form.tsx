// src/features/users/components/password-form.tsx
import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import {
  passwordChangeSchema,
  toPasswordChangePayload,
  type PasswordChangeInput,
} from "../schemas";
import { changeOwnPassword } from "../api";
import { HttpError, NetworkError } from "@/lib/api/types";

import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldGroup,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

type SubmitFeedback =
  | { kind: "idle" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export function PasswordForm() {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  const form = useForm<PasswordChangeInput>({
    mode: "onChange",
    resolver: zodResolver(passwordChangeSchema),
    defaultValues: {
      oldPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  async function onSubmit(data: PasswordChangeInput) {
    setFeedback({ kind: "idle" });

    try {
      await changeOwnPassword(toPasswordChangePayload(data));
      form.reset();
      setFeedback({ kind: "success", message: "Password updated." });
    } catch (error: unknown) {
      if (error instanceof HttpError) {
        const details = error.details;

        // 422: map backend snake_case field names back to form fields.
        if (error.status === 422 && Array.isArray(details)) {
          for (const err of details) {
            const rawField = err.loc[err.loc.length - 1];
            if (rawField === "old_password") {
              form.setError("oldPassword", {
                type: "server",
                message: err.msg,
              });
            } else if (rawField === "new_password") {
              form.setError("newPassword", {
                type: "server",
                message: err.msg,
              });
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
          message: error.message || "Failed to update password.",
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

  const { isSubmitting, isValid } = form.formState;

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {feedback.kind === "success" && (
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

      <FieldGroup>
        <Controller
          control={form.control}
          name="oldPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Current Password</FieldLabel>
              <Input
                id={field.name}
                type="password"
                autoComplete="current-password"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="newPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>New Password</FieldLabel>
              <Input
                id={field.name}
                type="password"
                autoComplete="new-password"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              <FieldDescription>
                At least 8 characters, with an uppercase letter, a lowercase
                letter, a number, and a special character.
              </FieldDescription>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="confirmPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Confirm New Password</FieldLabel>
              <Input
                id={field.name}
                type="password"
                autoComplete="new-password"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />
      </FieldGroup>

      <Button type="submit" disabled={isSubmitting || !isValid}>
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Updating...
          </>
        ) : (
          "Update Password"
        )}
      </Button>
    </form>
  );
}
