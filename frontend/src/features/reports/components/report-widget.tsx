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
import { getErrorMessage } from "@/lib/api/error-message";
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
        setTaskId(data.task_id);
      } else {
        downloadMutation.mutate();
      }
    },
  });

  const statusQuery = useReportStatus(taskId ?? undefined);

  const reportAlreadyExists = generateMutation.data?.status === "ready";
  const pollingCompleted = statusQuery.data?.status === "completed";
  const isReportReady = reportAlreadyExists || pollingCompleted;

  const isFailed = statusQuery.data?.status === "failed";
  const isGenerating =
    Boolean(taskId) && !isReportReady && !isFailed && !statusQuery.error;

  const generateError = generateMutation.isError
    ? getErrorMessage(
        generateMutation.error,
        "Failed to start report generation.",
      )
    : null;

  const downloadError = downloadMutation.isError
    ? getErrorMessage(
        downloadMutation.error,
        "Failed to download the report. Please try again.",
      )
    : null;

  function handleRetry() {
    setTaskId(null);
    generateMutation.reset();
    downloadMutation.reset();
  }

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
        {!taskId &&
          !generateMutation.isPending &&
          !generateError &&
          !reportAlreadyExists && (
            <Button onClick={() => generateMutation.mutate()}>
              <FileText className="mr-2 h-4 w-4" />
              Generate Report
            </Button>
          )}

        {generateMutation.isPending && (
          <Button disabled>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Starting...
          </Button>
        )}

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

        {taskId && statusQuery.error && !isReportReady && !isFailed && (
          <>
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {getErrorMessage(
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

        {/* Generated successfully, download. */}
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
