// src/features/users/components/reset-password-dialog.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2 } from "lucide-react";

import {
  adminPasswordResetSchema,
  toAdminPasswordResetPayload,
  type AdminPasswordResetInput,
} from "../schemas";
import { changeUserPassword } from "../api";
import { handleFormError } from "@/lib/forms/handle-form-error";
import type { User } from "@/types";

import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type SubmitFeedback = { kind: "idle" } | { kind: "error"; message: string };

interface ResetPasswordDialogProps {
  user: User;
  onOpenChange: (open: boolean) => void;
}

export function ResetPasswordDialog({
  user,
  onOpenChange,
}: ResetPasswordDialogProps) {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  const form = useForm<AdminPasswordResetInput>({
    mode: "onChange",
    resolver: zodResolver(adminPasswordResetSchema),
    defaultValues: {
      oldPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const mutation = useMutation({
    mutationKey: ["users", "reset-password", user.id],
    mutationFn: (data: AdminPasswordResetInput) =>
      changeUserPassword(user.id, toAdminPasswordResetPayload(data)),
    onSuccess: () => {
      onOpenChange(false);
    },
    onError: (error) => {
      handleFormError(error, {
        form,
        fieldMap: {
          old_password: "oldPassword",
          new_password: "newPassword",
        },
        setFormError: (msg) => setFeedback({ kind: "error", message: msg }),
        fallback: "Failed to reset password.",
      });
    },
  });

  function onSubmit(data: AdminPasswordResetInput) {
    setFeedback({ kind: "idle" });
    mutation.mutate(data);
  }

  const { isValid } = form.formState;
  const isSubmitting = mutation.isPending;

  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!isSubmitting) onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reset password</DialogTitle>
          <DialogDescription>
            Set a new password for{" "}
            <strong className="text-foreground">{user.username}</strong>.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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
                  <FieldLabel htmlFor={field.name}>Current password</FieldLabel>
                  <Input
                    id={field.name}
                    type="password"
                    autoComplete="off"
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  <FieldDescription>
                    Required by the current backend contract. If you don't know
                    the user's current password, the backend needs to be updated
                    to make this optional for admin resets.
                  </FieldDescription>
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            <Controller
              control={form.control}
              name="newPassword"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>New password</FieldLabel>
                  <Input
                    id={field.name}
                    type="password"
                    autoComplete="new-password"
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  <FieldDescription>
                    At least 8 characters, with uppercase, lowercase, a number,
                    and a special character.
                  </FieldDescription>
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            <Controller
              control={form.control}
              name="confirmPassword"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>
                    Confirm new password
                  </FieldLabel>
                  <Input
                    id={field.name}
                    type="password"
                    autoComplete="new-password"
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
          </FieldGroup>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Resetting...
                </>
              ) : (
                "Reset password"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
