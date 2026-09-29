// src/pages/analysis/analysis-detail-page.tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { AlertCircle } from "lucide-react";

import { getAnalysis } from "@/features/analysis/api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { AnalysisDetailed, RiskLevel } from "@/types/analysis";
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

/**
 * Route component. Reads the URL param, validates it, and hands off to a
 * keyed view. Navigating from /analysis/1 to /analysis/2 changes the key,
 * which remounts the view with fresh state — no manual state reset needed.
 *
 * Rationale: within a single mount, the URL param never changes on its own;
 * React Router reuses the same component instance across param changes. The
 * `key` prop tells React "this is a different resource, treat it as a new
 * component instance."
 */
export function AnalysisDetailPage() {
  const { analysisId } = useParams();
  const id = Number(analysisId);
  const isValidId = Number.isInteger(id) && id > 0;

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

  return <AnalysisDetailView key={id} analysisId={id} />;
}

interface AnalysisDetailViewProps {
  analysisId: number;
}

/**
 * Stateful view for a single analysis. Because the parent keys this on
 * analysisId, every navigation to a different analysis is a fresh mount
 * with clean state — the effect no longer needs to reset anything.
 *
 * The only setState calls are inside the async IIFE (after an await), which
 * is the legitimate use case the eslint rule permits.
 */
function AnalysisDetailView({ analysisId }: AnalysisDetailViewProps) {
  const [analysis, setAnalysis] = useState<AnalysisDetailed | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getAnalysis(analysisId);
        if (cancelled) return;
        setAnalysis(data);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof HttpError
            ? err.status === 404
              ? "Analysis not found."
              : err.message
            : err instanceof NetworkError
              ? err.message
              : "Failed to load analysis.",
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [analysisId]);

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
          <AlertDescription>{error ?? "Analysis not found."}</AlertDescription>
        </Alert>
        {/* TEMP DIAGNOSTIC */}
        <pre className="mt-4 rounded bg-muted p-4 text-xs overflow-auto">
          {JSON.stringify(
            { error, hasAnalysis: Boolean(analysis), analysisId },
            null,
            2,
          )}
        </pre>
        <Button className="mt-4" render={<Link to="/dashboard" />}>
          Back to dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 md:p-8">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">{analysis.title}</h2>
        {analysis.description && (
          <p className="mt-1 text-muted-foreground">{analysis.description}</p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{analysis.document_type}</Badge>
          <Badge variant="outline">
            Risk score: {analysis.overall_risk_score}/10
          </Badge>
        </div>
      </div>

      {/* Document summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Document Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{analysis.document_summary}</p>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {analysis.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {analysis.recommendations.map((rec) => (
                <li key={rec}>{rec}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Clauses */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Clauses</h3>
        {analysis.clauses.map((clause) => (
          <Card key={clause.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-base">
                    {clause.clause_type}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {clause.summary}
                  </CardDescription>
                </div>
                <Badge
                  className={cn(
                    "capitalize",
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
                    <Badge key={term} variant="outline" className="font-normal">
                      {term}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium">Suggested actions</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {clause.suggested_actions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
