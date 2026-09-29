import { z } from "zod";
import type { AnalysisCreate } from "@/types";

export const analysisCreateSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required")
    .max(200, "Title must not exceed 200 characters"),

  text: z.string().min(10, "Contract text must be at least 10 characters"), // UI-specific minimum

  description: z.string().nullable().optional(),
});

// Infer the TS type from the schema (used by the form component)
export type AnalysisCreateInput = z.infer<typeof analysisCreateSchema>;

// Compile-time assertion: Guarantees our Zod schema satisfies the FastAPI contract.
// If you remove a required field from Zod, TS will throw an error here.
type AssertAssignable = AnalysisCreateInput extends AnalysisCreate
  ? true
  : never;
const _: AssertAssignable = true;
void _;
