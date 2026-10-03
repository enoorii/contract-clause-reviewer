// src/features/users/components/create-user-dialog.tsx
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2 } from "lucide-react";

import {
  userCreateSchema,
  toUserCreatePayload,
  type UserCreateInput,
} from "../schemas";
import { createUser } from "../api";
import { HttpError, NetworkError } from "@/lib/api/types";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type SubmitFeedback = { kind: "idle" } | { kind: "error"; message: string };

interface CreateUserDialogProps {
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function CreateUserDialog({
  onOpenChange,
  onSuccess,
}: CreateUserDialogProps) {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  const form = useForm<UserCreateInput>({
    mode: "onChange",
    resolver: zodResolver(userCreateSchema),
    defaultValues: { username: "", password: "", role: "user" },
  });

  async function onSubmit(data: UserCreateInput) {
    setFeedback({ kind: "idle" });

    try {
      await createUser(toUserCreatePayload(data));
      form.reset();
      onSuccess();
      onOpenChange(false);
    } catch (error: unknown) {
      if (error instanceof HttpError) {
        const details = error.details;

        if (error.status === 422 && Array.isArray(details)) {
          for (const err of details) {
            const rawField = err.loc[err.loc.length - 1];
            if (rawField === "username" || rawField === "password") {
              form.setError(rawField, { type: "server", message: err.msg });
            } else {
              setFeedback({ kind: "error", message: err.msg });
            }
          }
          return;
        }

        setFeedback({
          kind: "error",
          message:
            typeof details === "string"
              ? details
              : error.message || "Failed to create user.",
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
    <Dialog
      open
      onOpenChange={(next) => {
        if (!isSubmitting) onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create user</DialogTitle>
          <DialogDescription>
            Add a new user account. The user will be able to log in with the
            credentials you set here.
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
              name="username"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>Username</FieldLabel>
                  <Input
                    id={field.name}
                    autoComplete="off"
                    aria-invalid={fieldState.invalid}
                    {...field}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            <Controller
              control={form.control}
              name="password"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>Password</FieldLabel>
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
              name="role"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>Role</FieldLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger
                      id={field.name}
                      aria-invalid={fieldState.invalid}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">User</SelectItem>
                      <SelectItem value="viewer">Viewer</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
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
                  Creating...
                </>
              ) : (
                "Create user"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
