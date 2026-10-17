// src/pages/dashboard/dashboard-page.tsx
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { FilePlus, AlertCircle } from "lucide-react";

import { getProfile } from "@/features/users/api";
import { getErrorMessage } from "@/lib/api/error-message";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardPage() {
  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["current-user"],
    staleTime: 10 * 60 * 1000,
    queryFn: getProfile,
  });

  const analyses = user?.analyses ?? [];

  return (
    <div className="p-6 md:p-8">
      <PageHeader
        title="Dashboard"
        description="Overview of your recent contract analyses."
        action={
          <Button render={<Link to="/analysis/new" />}>
            <FilePlus className="mr-2 h-4 w-4" />
            New Analysis
          </Button>
        }
      />

      <h3 className="mb-4 text-lg font-semibold">Recent Analyses</h3>

      {isLoading && !user ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="mt-2 h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="mb-2 h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {getErrorMessage(error, "Failed to load your profile.")}
          </AlertDescription>
        </Alert>
      ) : analyses.length === 0 ? (
        <EmptyState
          title="No analyses yet"
          description="Get started by submitting your first contract for review."
          action={
            <Button render={<Link to="/analysis/new" />}>
              <FilePlus className="mr-2 h-4 w-4" />
              Create Analysis
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {analyses.map((analysis) => (
            <Link
              key={analysis.id}
              to={`/analysis/${analysis.id}`}
              className="group block"
            >
              <Card className="transition-shadow hover:shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg">{analysis.title}</CardTitle>
                  {analysis.description && (
                    <CardDescription className="line-clamp-2">
                      {analysis.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">
                    Created:{" "}
                    {new Date(analysis.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
