// src/pages/admin/users-page.tsx
import { useState } from "react";
import { AlertCircle, UserPlus } from "lucide-react";

import { useAuth } from "@/lib/auth/hooks";
import { useUsersList } from "@/features/users/hooks";
import { useDebounce } from "@/hooks/use-debounce";
import { UserTable } from "@/features/users/components/user-table";
import { UsersFilters } from "@/features/users/components/users-filters";
import { UsersPagination } from "@/features/users/users-pagination";
import { CreateUserDialog } from "@/features/users/components/create-user-dialog";
import { EditUserDialog } from "@/features/users/components/edit-user-dialog";
import { DeleteUserDialog } from "@/features/users/components/delete-user-dialog";
import { ResetPasswordDialog } from "@/features/users/components/reset-password-dialog";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { Role, User } from "@/types";

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

type ActiveDialog =
  | { kind: "none" }
  | { kind: "create" }
  | { kind: "edit"; user: User }
  | { kind: "delete"; user: User }
  | { kind: "resetPassword"; user: User };

function listErrorMessage(err: unknown): string {
  if (err instanceof HttpError || err instanceof NetworkError) {
    return err.message;
  }
  return "Failed to load users.";
}

export function UsersPage() {
  const { user: currentUser } = useAuth();

  const [page, setPage] = useState(1);
  const [size, setSize] = useState(10);
  const [searchInput, setSearchInput] = useState("");
  const [role, setRole] = useState<Role | null>(null);
  const [isActive, setIsActive] = useState<boolean | null>(null);

  const [dialog, setDialog] = useState<ActiveDialog>({ kind: "none" });

  const debouncedSearch = useDebounce(searchInput, 300);

  const { data, isLoading, error } = useUsersList({
    page,
    size,
    search: debouncedSearch || null,
    role,
    is_active: isActive,
  });

  function handleSearchChange(value: string) {
    setSearchInput(value);
    setPage(1);
  }

  function handleRoleChange(value: Role | null) {
    setRole(value);
    setPage(1);
  }

  function handleIsActiveChange(value: boolean | null) {
    setIsActive(value);
    setPage(1);
  }

  function handleSizeChange(newSize: number) {
    setSize(newSize);
    setPage(1);
  }

  function closeDialog() {
    setDialog({ kind: "none" });
  }

  return (
    <div className="p-6 md:p-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Users</h2>
          <p className="mt-1 text-muted-foreground">
            Manage user accounts and permissions.
          </p>
        </div>
        <Button onClick={() => setDialog({ kind: "create" })}>
          <UserPlus className="mr-2 h-4 w-4" />
          Create user
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">All users</CardTitle>
          <CardDescription>
            Filter, search, and manage every account in the system.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <UsersFilters
            search={searchInput}
            onSearchChange={handleSearchChange}
            role={role}
            onRoleChange={handleRoleChange}
            isActive={isActive}
            onIsActiveChange={handleIsActiveChange}
          />

          {isLoading && !data && <TableSkeleton />}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{listErrorMessage(error)}</AlertDescription>
            </Alert>
          )}

          {data && data.items.length === 0 && <EmptyState />}

          {data && data.items.length > 0 && (
            <>
              <div className="rounded-md border">
                <UserTable
                  users={data.items}
                  currentUserId={currentUser?.id}
                  onEdit={(user) => setDialog({ kind: "edit", user })}
                  onResetPassword={(user) =>
                    setDialog({ kind: "resetPassword", user })
                  }
                  onDelete={(user) => setDialog({ kind: "delete", user })}
                />
              </div>

              <UsersPagination
                page={data.page}
                pages={data.pages}
                total={data.total}
                size={data.size}
                onPageChange={setPage}
                onSizeChange={handleSizeChange}
              />
            </>
          )}
        </CardContent>
      </Card>

      {dialog.kind === "create" && (
        <CreateUserDialog onOpenChange={closeDialog} />
      )}

      {dialog.kind === "edit" && (
        <EditUserDialog
          key={dialog.user.id}
          user={dialog.user}
          onOpenChange={closeDialog}
        />
      )}

      {dialog.kind === "delete" && (
        <DeleteUserDialog user={dialog.user} onOpenChange={closeDialog} />
      )}

      {dialog.kind === "resetPassword" && (
        <ResetPasswordDialog
          key={dialog.user.id}
          user={dialog.user}
          onOpenChange={closeDialog}
        />
      )}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed p-12 text-center">
      <p className="text-sm font-medium">No users found</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Try adjusting your search or filters, or create a new user.
      </p>
    </div>
  );
}
