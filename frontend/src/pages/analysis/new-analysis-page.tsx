import { AnalysisForm } from "@/features/analysis/analysis-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function NewAnalysisPage() {
  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight">New Analysis</h2>
        <p className="mt-1 text-muted-foreground">
          Submit a contract document for AI-powered risk analysis and clause
          extraction.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Document Details</CardTitle>
          <CardDescription>
            Provide the contract text and metadata to begin the review process.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AnalysisForm />
        </CardContent>
      </Card>
    </div>
  );
}
