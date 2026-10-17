// src/pages/profile/profile-page.tsx
import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";

import { getProfile } from "@/features/users/api";
import { UsernameForm } from "@/features/users/components/username-form";
import { PasswordForm } from "@/features/users/components/password-form";
import { getErrorMessage } from "@/lib/api/error-message";
import { PageHeader } from "@/components/common/page-header";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ProfilePage() {
  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["current-user"],
    queryFn: getProfile,
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="mx-auto max-w-3xl p-6 md:p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error
              ? getErrorMessage(error, "Failed to load profile.")
              : "Profile not available."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
      <PageHeader
        title="Profile"
        description="Manage your account information."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Account Information</CardTitle>
          <CardDescription>
            Some fields are read-only and can only be changed by an
            administrator.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                User ID
              </dt>
              <dd className="mt-1 break-all font-mono text-xs">{user.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Role
              </dt>
              <dd className="mt-1">
                <Badge variant="secondary" className="capitalize">
                  {user.role}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Status
              </dt>
              <dd className="mt-1">
                <Badge variant={user.is_active ? "default" : "destructive"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Username</CardTitle>
          <CardDescription>
            Change your username. This is what you use to log in.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UsernameForm initialUsername={user.username} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Password</CardTitle>
          <CardDescription>
            Change your password. You must provide your current password to
            confirm.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PasswordForm />
        </CardContent>
      </Card>
    </div>
  );
}
