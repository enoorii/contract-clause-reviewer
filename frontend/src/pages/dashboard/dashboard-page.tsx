import { useState, useEffect } from "react";
import { MOCK_ANALYSES } from "@/lib/mock-data";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { FilePlus } from "lucide-react";
import { Link } from "react-router";

export function DashboardPage() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="p-6 md:p-8">
      {/* Page Header Section */}
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

      {/* Content Section */}
      <h3 className="mb-4 text-lg font-semibold">Recent Analyses</h3>

      {isLoading ? (
        // Skeleton Loading State
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2 mt-2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-5/6" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : MOCK_ANALYSES.length === 0 ? (
        // Empty State
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <CardHeader>
            <CardTitle>No analyses yet</CardTitle>
            <CardDescription>
              Get started by submitting your first contract for review.
            </CardDescription>
          </CardHeader>
          <Button>
            <FilePlus className="mr-2 h-4 w-4" />
            Create Analysis
          </Button>
        </Card>
      ) : (
        // Data List (using Grid instead of UL for better card layouts)
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {MOCK_ANALYSES.map((analysis) => (
            <Link
              key={analysis.id}
              to={`/analysis/${analysis.id}`}
              className="group block"
            >
              <Card className="hover:shadow-md transition-shadow">
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
