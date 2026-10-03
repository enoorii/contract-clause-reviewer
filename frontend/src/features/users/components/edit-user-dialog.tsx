// src/features/users/components/edit-user-dialog.tsx
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2 } from "lucide-react";

import {
  userUpdateSchema,
  toUserUpdatePayload,
  type UserUpdateInput,
} from "../schemas";
import { updateUser } from "../api";
import { HttpError, NetworkError } from "@/lib/api/types";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

type SubmitFeedback = { kind: "idle" } | { kind: "error"; message: string };

interface EditUserDialogProps {
  user: User;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function EditUserDialog({
  user,
  onOpenChange,
  onSuccess,
}: EditUserDialogProps) {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });

  const form = useForm<UserUpdateInput>({
    mode: "onChange",
    resolver: zodResolver(userUpdateSchema),
    defaultValues: {
      username: user.username,
      role: user.role,
      is_active: user.is_active,
    },
  });

  async function onSubmit(data: UserUpdateInput) {
    setFeedback({ kind: "idle" });

    try {
      await updateUser(user.id, toUserUpdatePayload(data));
      onSuccess();
      onOpenChange(false);
    } catch (error: unknown) {
      if (error instanceof HttpError) {
        const details = error.details;

        if (error.status === 422 && Array.isArray(details)) {
          for (const err of details) {
            const rawField = err.loc[err.loc.length - 1];
            if (
              rawField === "username" ||
              rawField === "role" ||
              rawField === "is_active"
            ) {
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
              : error.message || "Failed to update user.",
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
    <Dialog
      open
      onOpenChange={(next) => {
        if (!isSubmitting) onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
          <DialogDescription>
            Update account details for{" "}
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

            <Controller
              control={form.control}
              name="is_active"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <FieldLabel htmlFor={field.name}>Active</FieldLabel>
                      <FieldDescription>
                        Inactive users cannot log in.
                      </FieldDescription>
                    </div>
                    <Switch
                      id={field.name}
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      aria-invalid={fieldState.invalid}
                    />
                  </div>
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
            <Button
              type="submit"
              disabled={isSubmitting || !isValid || !isDirty}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save changes"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
