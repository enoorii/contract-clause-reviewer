// src/pages/reports/report-page.tsx
import { useParams } from "react-router";

export function ReportPage() {
  const { analysisId } = useParams();
  return (
    <div className="p-6 md:p-8">
      <h2 className="text-2xl font-bold tracking-tight">Report</h2>
      <p className="mt-1 text-muted-foreground">
        Report generation for analysis {analysisId} will be built in Phase 10.
      </p>
    </div>
  );
}
