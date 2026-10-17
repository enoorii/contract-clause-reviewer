import { AnalysisForm } from "@/features/analysis/analysis-form";
import { PageHeader } from "@/components/common/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function NewAnalysisPage() {
  return (
    <div className="mx-auto max-w-3xl p-6 md:p-8">
      <PageHeader
        title="New Analysis"
        description="Submit a contract document for AI-powered risk analysis and clause extraction."
      />

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
