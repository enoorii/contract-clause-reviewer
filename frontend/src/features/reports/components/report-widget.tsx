// src/features/reports/components/report-widget.tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
} from "lucide-react";

import { downloadReport, generateReport, triggerBrowserDownload } from "../api";
import { useReportStatus } from "../hooks";
import { HttpError, NetworkError } from "@/lib/api/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ReportWidgetProps {
  analysisId: number;
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpError || err instanceof NetworkError) {
    return err.message;
  }
  return fallback;
}

export function ReportWidget({ analysisId }: ReportWidgetProps) {
  // The only local state: which task we're polling. Set when the backend
  // queues a task. Cleared on "Start over".
  const [taskId, setTaskId] = useState<string | null>(null);

  // ── Mutations ───────────────────────────────────────────────────────
  // Download is defined first because generate's onSuccess may invoke it.
  const downloadMutation = useMutation({
    mutationKey: ["reports", "download", analysisId],
    mutationFn: () => downloadReport(analysisId),
    onSuccess: (blob) => {
      triggerBrowserDownload(blob, `report-${analysisId}.pdf`);
    },
  });

  const generateMutation = useMutation({
    mutationKey: ["reports", "generate", analysisId],
    mutationFn: () => generateReport(analysisId),
    onSuccess: (data) => {
      if (data.status === "queued") {
        // Start polling.
        setTaskId(data.task_id);
      } else {
        // Report already exists — download immediately.
        downloadMutation.mutate();
      }
    },
  });

  // ── Polling ─────────────────────────────────────────────────────────
  const statusQuery = useReportStatus(taskId ?? undefined);

  // ── Derived state ───────────────────────────────────────────────────
  const reportAlreadyExists = generateMutation.data?.status === "ready";
  const pollingCompleted = statusQuery.data?.status === "completed";
  const isReportReady = reportAlreadyExists || pollingCompleted;

  const isFailed = statusQuery.data?.status === "failed";
  const isGenerating =
    Boolean(taskId) && !isReportReady && !isFailed && !statusQuery.error;

  const generateError = generateMutation.isError
    ? errorMessage(generateMutation.error, "Failed to start report generation.")
    : null;

  const downloadError = downloadMutation.isError
    ? errorMessage(
        downloadMutation.error,
        "Failed to download the report. Please try again.",
      )
    : null;

  // ── Handlers ────────────────────────────────────────────────────────
  function handleRetry() {
    setTaskId(null);
    generateMutation.reset();
    downloadMutation.reset();
  }

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5" />
          Report
        </CardTitle>
        <CardDescription>
          Generate a PDF report summarising this contract analysis.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Idle — nothing started, no completed report, no errors */}
        {!taskId &&
          !generateMutation.isPending &&
          !generateError &&
          !reportAlreadyExists && (
            <Button onClick={() => generateMutation.mutate()}>
              <FileText className="mr-2 h-4 w-4" />
              Generate Report
            </Button>
          )}

        {/* Generating — the POST is in flight */}
        {generateMutation.isPending && (
          <Button disabled>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Starting...
          </Button>
        )}

        {/* Generate request failed */}
        {generateError && (
          <>
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{generateError}</AlertDescription>
            </Alert>
            <Button onClick={() => generateMutation.mutate()} variant="outline">
              Try again
            </Button>
          </>
        )}

        {/* Task queued or processing */}
        {isGenerating && (
          <div className="flex items-center gap-3 rounded-md border bg-muted/40 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <div className="space-y-0.5">
              <p className="text-sm font-medium">
                {!statusQuery.data ||
                statusQuery.data.status === "pending" ||
                statusQuery.data.status === "unknown"
                  ? "Queued"
                  : "Generating report"}
              </p>
              <p className="text-xs text-muted-foreground">
                This usually takes 10–30 seconds.
              </p>
            </div>
          </div>
        )}

        {/* Polling error — after MAX_CONSECUTIVE_ERRORS failures */}
        {taskId && statusQuery.error && !isReportReady && !isFailed && (
          <>
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {errorMessage(
                  statusQuery.error,
                  "Could not fetch report status.",
                )}
              </AlertDescription>
            </Alert>
            <Button onClick={handleRetry} variant="outline">
              Start over
            </Button>
          </>
        )}

        {/* Task failed */}
        {isFailed && (
          <>
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {statusQuery.data?.error ?? "Report generation failed."}
              </AlertDescription>
            </Alert>
            <Button onClick={handleRetry} variant="outline">
              Try again
            </Button>
          </>
        )}

        {/* Completed — ready to download */}
        {isReportReady && (
          <>
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription>Your report is ready.</AlertDescription>
            </Alert>
            <Button
              onClick={() => downloadMutation.mutate()}
              disabled={downloadMutation.isPending}
            >
              {downloadMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Downloading...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </>
              )}
            </Button>
            {downloadError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{downloadError}</AlertDescription>
              </Alert>
            )}
          </>
        )}

        {/* Loading the very first status response */}
        {statusQuery.isLoading && taskId && !generateMutation.isPending && (
          <div className="flex items-center gap-3 rounded-md border bg-muted/40 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Checking status...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
