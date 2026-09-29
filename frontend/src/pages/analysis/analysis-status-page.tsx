// src/pages/analysis/analysis-status-page.tsx
import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";

import { useAnalysisStatus } from "@/features/analysis/hooks";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function AnalysisStatusPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { status, isLoading, error } = useAnalysisStatus(taskId);

  // When the analysis finishes, swap the URL for the persistent resource.
  // `replace: true` keeps the ephemeral task URL out of browser history.
  useEffect(() => {
    if (status?.status === "completed" && status.analysis) {
      navigate(`/analysis/${status.analysis.id}`, { replace: true });
    }
  }, [status, navigate]);

  return (
    <div className="mx-auto max-w-2xl p-6 md:p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight">
          Analyzing Contract
        </h2>
        <p className="mt-1 text-muted-foreground">
          Our AI is reviewing your document. This usually takes 30–60 seconds.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isLoading && !status && (
              <Loader2 className="h-5 w-5 animate-spin" />
            )}
            {status?.status === "completed" && (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            )}
            {status?.status === "failed" && (
              <AlertCircle className="h-5 w-5 text-destructive" />
            )}
            <span>
              {!status && "Fetching status…"}
              {status?.status === "pending" && "Queued"}
              {status?.status === "processing" && "Processing"}
              {status?.status === "completed" && "Completed"}
              {status?.status === "failed" && "Failed"}
              {status?.status === "unknown" && "Unknown"}
            </span>
          </CardTitle>
          <CardDescription>
            Task ID: <span className="font-mono text-xs">{taskId}</span>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {(status?.status === "pending" ||
            status?.status === "processing" ||
            (!status && !error)) && (
            <p className="text-sm text-muted-foreground">
              Checking status every 5 seconds. You can safely leave this page
              and come back later — the analysis will appear on your dashboard
              once it finishes.
            </p>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Could not fetch status</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {status?.status === "failed" && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Analysis failed</AlertTitle>
              <AlertDescription>
                {status.error ?? "The analysis could not be completed."}
              </AlertDescription>
            </Alert>
          )}

          <Button
            variant="outline"
            render={
              <Link to="/dashboard">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to dashboard
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
