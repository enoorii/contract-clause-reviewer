// src/features/users/components/password-form.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react";

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
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

type SubmitFeedback =
  | { kind: "idle" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export function PasswordForm() {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  // Independent visibility state per field. Revealing the new password
  // should not reveal the confirmation (and vice versa).
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const form = useForm<PasswordChangeInput>({
    mode: "onChange",
    resolver: zodResolver(passwordChangeSchema),
    defaultValues: {
      oldPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const mutation = useMutation({
    mutationKey: ["profile", "change-password"],
    mutationFn: (data: PasswordChangeInput) =>
      changeOwnPassword(toPasswordChangePayload(data)),
    onSuccess: () => {
      form.reset();
      // Reset visibility on success — avoids surprising the user
      // if they re-open the form shortly after.
      setShowOld(false);
      setShowNew(false);
      setShowConfirm(false);
      setFeedback({ kind: "success", message: "Password updated." });
    },
    onError: (error) => {
      if (error instanceof HttpError) {
        const details = error.details;

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

        // 401 fallback (defense in depth if the backend reverts to 401)
        if (error.status === 401 && typeof details === "string") {
          form.setError("oldPassword", {
            type: "server",
            message: details,
          });
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
    },
  });

  function onSubmit(data: PasswordChangeInput) {
    setFeedback({ kind: "idle" });
    mutation.mutate(data);
  }

  const { isValid } = form.formState;
  const isSubmitting = mutation.isPending;

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
        {/* Current Password */}
        <Controller
          control={form.control}
          name="oldPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Current Password</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  id={field.name}
                  type={showOld ? "text" : "password"}
                  autoComplete="current-password"
                  aria-invalid={fieldState.invalid}
                  {...field}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    type="button"
                    size="icon-xs"
                    variant="ghost"
                    onClick={() => setShowOld((v) => !v)}
                    aria-label={showOld ? "Hide password" : "Show password"}
                  >
                    {showOld ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        {/* New Password */}
        <Controller
          control={form.control}
          name="newPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>New Password</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  id={field.name}
                  type={showNew ? "text" : "password"}
                  autoComplete="new-password"
                  aria-invalid={fieldState.invalid}
                  {...field}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    type="button"
                    size="icon-xs"
                    variant="ghost"
                    onClick={() => setShowNew((v) => !v)}
                    aria-label={showNew ? "Hide password" : "Show password"}
                  >
                    {showNew ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
              <FieldDescription>
                At least 8 characters, with an uppercase letter, a lowercase
                letter, a number, and a special character.
              </FieldDescription>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        {/* Confirm New Password */}
        <Controller
          control={form.control}
          name="confirmPassword"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Confirm New Password</FieldLabel>
              <InputGroup>
                <InputGroupInput
                  id={field.name}
                  type={showConfirm ? "text" : "password"}
                  autoComplete="new-password"
                  aria-invalid={fieldState.invalid}
                  {...field}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    type="button"
                    size="icon-xs"
                    variant="ghost"
                    onClick={() => setShowConfirm((v) => !v)}
                    aria-label={showConfirm ? "Hide password" : "Show password"}
                  >
                    {showConfirm ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
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
