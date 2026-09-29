// src/pages/dashboard/dashboard-page.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { FilePlus, AlertCircle } from "lucide-react";

import { getProfile } from "@/features/users/api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { UserDetailed } from "@/types/users";
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
  const [user, setUser] = useState<UserDetailed | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getProfile();
        if (!cancelled) setUser(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof HttpError || err instanceof NetworkError
              ? err.message
              : "Failed to load your profile.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const analyses = user?.analyses ?? [];

  return (
    <div className="p-6 md:p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Overview of your recent contract analyses.
          </p>
        </div>
        <Button render={<Link to="/analysis/new" />}>
          <FilePlus className="mr-2 h-4 w-4" />
          New Analysis
        </Button>
      </div>

      <h3 className="mb-4 text-lg font-semibold">Recent Analyses</h3>

      {isLoading ? (
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
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : analyses.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <CardHeader>
            <CardTitle>No analyses yet</CardTitle>
            <CardDescription>
              Get started by submitting your first contract for review.
            </CardDescription>
          </CardHeader>
          <Button render={<Link to="/analysis/new" />}>
            <FilePlus className="mr-2 h-4 w-4" />
            Create Analysis
          </Button>
        </Card>
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
