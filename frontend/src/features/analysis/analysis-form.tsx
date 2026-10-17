import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router";
import { Loader2 } from "lucide-react";

import { analysisCreateSchema, type AnalysisCreateInput } from "./schemas";
import { submitAnalysis } from "./api";
import { HttpError, NetworkError } from "@/lib/api/types";

import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldGroup,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function AnalysisForm() {
  const navigate = useNavigate();
  const [globalError, setGlobalError] = useState<string | null>(null);

  const form = useForm<AnalysisCreateInput>({
    mode: "onTouched",
    resolver: zodResolver(analysisCreateSchema),
    defaultValues: {
      title: "",
      text: "",
      description: "",
    },
  });

  const mutation = useMutation({
    mutationKey: ["analysis", "submit"],
    mutationFn: submitAnalysis,
    onSuccess: (response) => {
      navigate(`/analysis/status/${response.task_id}`);
    },
    onError: (error, variables) => {
      if (error instanceof HttpError) {
        const details = error.details;

        // 422: FastAPI validation errors → map to form fields
        if (error.status === 422 && Array.isArray(details)) {
          for (const err of details) {
            const fieldName = err.loc[err.loc.length - 1];

            if (typeof fieldName === "string" && fieldName in variables) {
              form.setError(fieldName as keyof AnalysisCreateInput, {
                type: "server",
                message: err.msg,
              });
            } else {
              setGlobalError(err.msg);
            }
          }
          return;
        }

        // Business logic errors: 400, 403, 404, 500 with a string detail
        if (typeof details === "string") {
          setGlobalError(details);
          return;
        }

        setGlobalError(error.message || "An unexpected server error occurred.");
        return;
      }

      setGlobalError(
        error instanceof NetworkError
          ? error.message
          : "An unexpected error occurred.",
      );
    },
  });

  function onSubmit(data: AnalysisCreateInput) {
    setGlobalError(null);
    mutation.mutate(data);
  }

  const isSubmitting = mutation.isPending;
  const isDisabled = isSubmitting || !form.formState.isValid;

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      {globalError && (
        <Alert variant="destructive">
          <AlertDescription>{globalError}</AlertDescription>
        </Alert>
      )}

      <FieldGroup>
        <Controller
          control={form.control}
          name="title"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Contract Title</FieldLabel>
              <Input
                id={field.name}
                placeholder="e.g., Master Services Agreement"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              <FieldDescription>
                A short, descriptive title for the contract (max 200
                characters).
              </FieldDescription>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="text"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>Contract Text</FieldLabel>
              <Textarea
                id={field.name}
                placeholder="Paste the full contract text here..."
                className="min-h-50 font-mono text-sm"
                aria-invalid={fieldState.invalid}
                {...field}
              />
              <FieldDescription>
                The raw text of the contract to be analyzed by the AI.
              </FieldDescription>
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />

        <Controller
          control={form.control}
          name="description"
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={field.name}>
                Description (Optional)
              </FieldLabel>
              <Textarea
                id={field.name}
                placeholder="Any additional context or specific clauses to look out for..."
                aria-invalid={fieldState.invalid}
                {...field}
                value={field.value ?? ""}
              />
              {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
            </Field>
          )}
        />
      </FieldGroup>

      <Button type="submit" disabled={isDisabled} className="w-full md:w-auto">
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Submitting...
          </>
        ) : (
          "Start Analysis"
        )}
      </Button>
    </form>
  );
}
