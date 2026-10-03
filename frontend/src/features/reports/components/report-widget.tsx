// src/features/reports/components/report-widget.tsx
import { useState } from "react";
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

export function ReportWidget({ analysisId }: ReportWidgetProps) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  // True when the backend told us the report already exists (303 redirect)
  // and we successfully downloaded it via the fallback path.
  const [reportReady, setReportReady] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const {
    status,
    isLoading: isPollLoading,
    error: pollError,
  } = useReportStatus(taskId ?? undefined);

  // ─── Actions ────────────────────────────────────────────────────────

  async function handleGenerate() {
    setIsSubmitting(true);
    setGenerateError(null);
    setDownloadError(null);

    try {
      const result = await generateReport(analysisId);
      setTaskId(result.task_id);
    } catch (err) {
      // The "already exists" case: backend returned 303 → fetch followed
      // to the PDF → our JSON parser threw. Fall back to direct download.
      // If it succeeds, the report was already there.
      try {
        const blob = await downloadReport(analysisId);
        triggerBrowserDownload(blob, `report-${analysisId}.pdf`);
        setReportReady(true);
      } catch {
        setGenerateError(
          err instanceof HttpError || err instanceof NetworkError
            ? err.message
            : "Failed to start report generation.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDownload() {
    setIsDownloading(true);
    setDownloadError(null);

    try {
      const blob = await downloadReport(analysisId);
      triggerBrowserDownload(blob, `report-${analysisId}.pdf`);
    } catch {
      setDownloadError("Failed to download the report. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  }

  function handleRetry() {
    setTaskId(null);
    setGenerateError(null);
    setDownloadError(null);
    setReportReady(false);
  }

  // ─── Derived state ──────────────────────────────────────────────────

  const isCompleted = status?.status === "completed" || reportReady;
  const isFailed = status?.status === "failed";
  const isGenerating =
    Boolean(taskId) &&
    !isCompleted &&
    !isFailed &&
    !pollError &&
    !generateError;

  // ─── Render ─────────────────────────────────────────────────────────

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
        {/* Idle — no task started, no completed report in state */}
        {!taskId && !isSubmitting && !generateError && !reportReady && (
          <Button onClick={handleGenerate}>
            <FileText className="mr-2 h-4 w-4" />
            Generate Report
          </Button>
        )}

        {/* Submitting the generate request */}
        {isSubmitting && (
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
            <Button onClick={handleGenerate} variant="outline">
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
                {!status ||
                status.status === "pending" ||
                status.status === "unknown"
                  ? "Queued"
                  : "Generating report"}
              </p>
              <p className="text-xs text-muted-foreground">
                This usually takes 10–30 seconds.
              </p>
            </div>
          </div>
        )}

        {/* Polling error — after 3 consecutive failures */}
        {taskId && pollError && !isCompleted && !isFailed && (
          <>
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{pollError}</AlertDescription>
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
                {status?.error ?? "Report generation failed."}
              </AlertDescription>
            </Alert>
            <Button onClick={handleRetry} variant="outline">
              Try again
            </Button>
          </>
        )}

        {/* Completed — ready to download */}
        {isCompleted && (
          <>
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription>Your report is ready.</AlertDescription>
            </Alert>
            <Button onClick={handleDownload} disabled={isDownloading}>
              {isDownloading ? (
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
        {isPollLoading && !status && !isSubmitting && taskId && (
          <div className="flex items-center gap-3 rounded-md border bg-muted/40 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Checking status...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
