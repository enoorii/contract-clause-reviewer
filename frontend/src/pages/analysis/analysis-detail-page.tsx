// src/pages/analysis/analysis-detail-page.tsx
import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";

import { getAnalysis } from "@/features/analysis/api";
import { ReportWidget } from "@/features/reports/components/report-widget";
import { getErrorMessage } from "@/lib/api/error-message";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { HttpError } from "@/lib/api/types";
import type { RiskLevel } from "@/types/analysis";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function riskBadgeClass(level: RiskLevel): string {
  switch (level) {
    case "low":
      return "border-transparent bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300";
    case "average":
      return "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300";
    case "high":
      return "border-transparent bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300";
    case "critical":
      return "border-transparent bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300";
  }
}

function analysisErrorMessage(err: unknown): string {
  if (err instanceof HttpError && err.status === 404) {
    return "Analysis not found.";
  }
  return getErrorMessage(err, "Failed to load analysis.");
}

export function AnalysisDetailPage() {
  const { analysisId } = useParams();
  const id = Number(analysisId);
  const isValidId = Number.isInteger(id) && id > 0;

  const {
    data: analysis,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["analysis-detail", id],
    queryFn: () => getAnalysis(id),
    enabled: isValidId,
  });

  if (!isValidId) {
    return (
      <div className="p-6 md:p-8">
        <h2 className="text-2xl font-bold tracking-tight">
          Analysis not found
        </h2>
        <p className="mt-1 text-muted-foreground">
          Invalid analysis id: <span className="font-mono">{analysisId}</span>.
        </p>
        <Button className="mt-4" render={<Link to="/dashboard" />}>
          Back to dashboard
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6 md:p-8">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="p-6 md:p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error ? analysisErrorMessage(error) : "Analysis not found."}
          </AlertDescription>
        </Alert>
        <Button className="mt-4" render={<Link to="/dashboard" />}>
          Back to dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 md:p-8">
      {/* Page header — add min-w-0 so long titles can truncate */}
      <div className="min-w-0">
        <PageHeader
          title={analysis.title}
          description={analysis.description ?? undefined}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{analysis.document_type}</Badge>
          <Badge variant="outline">
            Risk score: {analysis.overall_risk_score}/10
          </Badge>
        </div>
      </div>

      <ReportWidget analysisId={analysis.id} />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Document Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed wrap-break-word">
            {analysis.document_summary}
          </p>
        </CardContent>
      </Card>

      {analysis.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {analysis.recommendations.map((rec) => (
                <li key={rec} className="wrap-break-word">
                  {rec}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Clauses</h3>

        {analysis.clauses.length === 0 ? (
          <EmptyState
            title="No clauses identified"
            description="This document may be too short or contain no analyzable clauses."
          />
        ) : (
          analysis.clauses.map((clause) => (
            <Card key={clause.id}>
              <CardHeader>
                {/* min-w-0 allows the inner div to shrink; badge stays pinned */}
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-base wrap-break-word">
                      {clause.clause_type}
                    </CardTitle>
                    <CardDescription className="mt-1 wrap-break-word">
                      {clause.summary}
                    </CardDescription>
                  </div>
                  <Badge
                    className={cn(
                      "shrink-0 capitalize",
                      riskBadgeClass(clause.risk_level),
                    )}
                  >
                    {clause.risk_level}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm font-medium">Key terms</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {clause.key_terms.map((term) => (
                      <span
                        key={term}
                        className="inline-flex max-w-full items-center rounded-md border px-2 py-0.5 text-xs font-normal wrap-break-word"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium">Suggested actions</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {clause.suggested_actions.map((action) => (
                      <li key={action} className="wrap-break-word">
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
