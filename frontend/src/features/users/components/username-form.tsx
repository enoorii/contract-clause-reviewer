// src/features/users/components/username-form.tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import { usernameUpdateSchema, type UsernameUpdateInput } from "../schemas";
import { updateProfile } from "../api";
import { useAuth } from "@/lib/auth/hooks";
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

type SubmitFeedback =
  | { kind: "idle" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

interface UsernameFormProps {
  initialUsername: string;
}

export function UsernameForm({ initialUsername }: UsernameFormProps) {
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });
  const queryClient = useQueryClient();
  const { updateUser } = useAuth();

  const form = useForm<UsernameUpdateInput>({
    mode: "onChange",
    resolver: zodResolver(usernameUpdateSchema),
    defaultValues: { username: initialUsername },
  });

  const mutation = useMutation({
    mutationKey: ["profile", "update-username"],
    mutationFn: (data: UsernameUpdateInput) => updateProfile(data.username),
    onSuccess: (updated) => {
      form.reset({ username: updated.username });
      setFeedback({ kind: "success", message: "Username updated." });
      // Sync two sources of truth:
      // 1) the auth context (for the header and any useAuth().user consumer)
      // 2) the query cache (for profile page, dashboard, etc.)
      updateUser({ username: updated.username });
      queryClient.invalidateQueries({ queryKey: ["current-user"] });
      queryClient.invalidateQueries({ queryKey: ["users-list"] });
    },
    onError: (error) => {
      if (error instanceof HttpError) {
        const details = error.details;

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
    },
  });

  function onSubmit(data: UsernameUpdateInput) {
    setFeedback({ kind: "idle" });
    mutation.mutate(data);
  }

  const { isValid, isDirty } = form.formState;
  const isSubmitting = mutation.isPending;

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
