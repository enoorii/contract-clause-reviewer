import { Link, useParams } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getMockAnalysisDetail } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types";

// Risk colors are domain-specific (green→red), not part of the semantic
// theme palette, so hardcoded color classes are appropriate here.
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

export function AnalysisDetailPage() {
  // URL params are ALWAYS strings, so we convert to number.
  const { analysisId } = useParams();
  const id = Number(analysisId);
  const analysis = getMockAnalysisDetail(id);

  // Type narrowing: handles /analysis/999 or /analysis/not-a-number
  if (!analysis) {
    return (
      <div className="p-6 md:p-8">
        <h2 className="text-2xl font-bold tracking-tight">
          Analysis not found
        </h2>
        <p className="mt-1 text-muted-foreground">
          No analysis exists with id{" "}
          <span className="font-mono">{analysisId}</span>.
        </p>
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
