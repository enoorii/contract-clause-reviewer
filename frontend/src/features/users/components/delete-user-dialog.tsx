// src/features/users/components/delete-user-dialog.tsx
import { useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import { deleteUser } from "../api";
import { HttpError, NetworkError } from "@/lib/api/types";
import type { User } from "@/types";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface DeleteUserDialogProps {
  user: User;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function DeleteUserDialog({
  user,
  onOpenChange,
  onSuccess,
}: DeleteUserDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setIsSubmitting(true);
    setError(null);

    try {
      await deleteUser(user.id);
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      setError(
        err instanceof HttpError || err instanceof NetworkError
          ? err.message
          : "Failed to delete user.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AlertDialog
      open
      onOpenChange={(next) => {
        if (!isSubmitting) onOpenChange(next);
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete user?</AlertDialogTitle>
          <AlertDialogDescription>
            This will inactivate{" "}
            <strong className="text-foreground">{user.username}</strong>. This
            action can be undone. This applies a{" "}
            <strong className="text-foreground">soft delete</strong>.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              "Delete user"
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
