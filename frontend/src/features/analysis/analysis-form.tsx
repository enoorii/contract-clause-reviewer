import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router";
import { z } from "zod";
import { Loader2 } from "lucide-react";

import { analysisCreateSchema } from "./schemas";
import { submitAnalysis } from "./api";
import { handleFormError } from "@/lib/forms/handle-form-error";

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

// The schema uses `.transform()` on `description`, so `z.input` and `z.output`
// differ: input allows `description` to be absent, output normalizes it to
// `string | undefined`. React Hook Form v7 needs both types in its three-generic
// form: `useForm<TFieldValues, TContext, TTransformedValues>`.
type AnalysisFormInput = z.input<typeof analysisCreateSchema>;
type AnalysisFormOutput = z.output<typeof analysisCreateSchema>;

export function AnalysisForm() {
  const navigate = useNavigate();
  const [globalError, setGlobalError] = useState<string | null>(null);

  const form = useForm<AnalysisFormInput, unknown, AnalysisFormOutput>({
    mode: "onTouched",
    resolver: zodResolver(analysisCreateSchema),
    defaultValues: { title: "", text: "", description: "" },
  });

  const mutation = useMutation({
    mutationKey: ["analysis", "submit"],
    mutationFn: submitAnalysis,
    onSuccess: (response) => {
      navigate(`/analysis/status/${response.task_id}`);
    },
    onError: (error) => {
      handleFormError(error, {
        form,
        setFormError: setGlobalError,
        fallback: "An unexpected server error occurred.",
      });
    },
  });

  function onSubmit(data: AnalysisFormOutput) {
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
