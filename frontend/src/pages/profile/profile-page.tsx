// src/pages/profile/profile-page.tsx
import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";

import { getProfile } from "@/features/users/api";
import { UsernameForm } from "@/features/users/components/username-form";
import { PasswordForm } from "@/features/users/components/password-form";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { UserDetailed } from "@/types";

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
  const [user, setUser] = useState<UserDetailed | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getProfile();
        if (cancelled) return;
        setUser(data);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof HttpError || err instanceof NetworkError
            ? err.message
            : "Failed to load profile.",
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

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
            {error ?? "Profile not available."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Profile</h2>
        <p className="mt-1 text-muted-foreground">
          Manage your account information.
        </p>
      </div>

      {/* Read-only account info */}
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

      {/* Username form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Username</CardTitle>
          <CardDescription>
            Change your username. This is what you use to log in.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UsernameForm
            initialUsername={user.username}
            onSuccess={(newUsername) =>
              setUser((prev) =>
                prev ? { ...prev, username: newUsername } : prev,
              )
            }
          />
        </CardContent>
      </Card>

      {/* Password form */}
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
