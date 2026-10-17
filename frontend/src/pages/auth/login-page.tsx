// src/pages/auth/login-page.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useLocation } from "react-router";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";

import { loginSchema, type LoginInput } from "@/features/auth/schemas";
import { useAuth } from "@/lib/auth/hooks";
import { getErrorMessage } from "@/lib/api/error-message";
import { HttpError } from "@/lib/api/types";

import {
  Field,
  FieldLabel,
  FieldError,
  FieldGroup,
} from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type SubmitFeedback = { kind: "idle" } | { kind: "error"; message: string };

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [feedback, setFeedback] = useState<SubmitFeedback>({ kind: "idle" });
  const [showPassword, setShowPassword] = useState(false);

  const from =
    (location.state as { from?: Location })?.from?.pathname || "/dashboard";

  const form = useForm<LoginInput>({
    mode: "onChange",
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const mutation = useMutation({
    mutationKey: ["auth", "login"],
    mutationFn: async (data: LoginInput) => {
      await login(data.username, data.password);
    },
    onSuccess: () => {
      navigate(from, { replace: true });
    },
    onError: (error) => {
      if (
        error instanceof HttpError &&
        (error.status === 401 || error.status === 403)
      ) {
        setFeedback({
          kind: "error",
          message: "Invalid username or password.",
        });
        return;
      }
      setFeedback({
        kind: "error",
        message: getErrorMessage(error, "Login failed. Please try again."),
      });
    },
  });

  function onSubmit(data: LoginInput) {
    setFeedback({ kind: "idle" });
    mutation.mutate(data);
  }

  const { isValid } = form.formState;
  const isSubmitting = mutation.isPending;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>
            Enter your credentials to access the Contract Clause Reviewer.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {feedback.kind === "error" && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{feedback.message}</AlertDescription>
              </Alert>
            )}

            <FieldGroup>
              {/* Username — wrapped in InputGroup for consistent sizing */}
              <Controller
                control={form.control}
                name="username"
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>Username</FieldLabel>
                    <InputGroup>
                      <InputGroupInput
                        id={field.name}
                        type="text"
                        autoComplete="username"
                        autoFocus
                        aria-invalid={fieldState.invalid}
                        disabled={isSubmitting}
                        {...field}
                      />
                    </InputGroup>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              {/* Password — same pattern as PasswordForm */}
              <Controller
                control={form.control}
                name="password"
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>Password</FieldLabel>
                    <InputGroup>
                      <InputGroupInput
                        id={field.name}
                        type={showPassword ? "text" : "password"}
                        autoComplete="current-password"
                        aria-invalid={fieldState.invalid}
                        disabled={isSubmitting}
                        {...field}
                      />
                      <InputGroupAddon align="inline-end">
                        <InputGroupButton
                          type="button"
                          size="icon-xs"
                          variant="ghost"
                          onClick={() => setShowPassword((v) => !v)}
                          aria-label={
                            showPassword ? "Hide password" : "Show password"
                          }
                          disabled={isSubmitting}
                        >
                          {showPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </InputGroupButton>
                      </InputGroupAddon>
                    </InputGroup>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            </FieldGroup>

            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting || !isValid}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
