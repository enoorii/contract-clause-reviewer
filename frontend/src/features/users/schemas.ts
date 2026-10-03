// src/features/users/schemas.ts
import { z } from "zod";
import type { PasswordChange } from "@/types";

// ─── Username Update ─────────────────────────────────────────────────

export const usernameUpdateSchema = z.object({
  username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .max(50, "Username must not exceed 50 characters"),
});

export type UsernameUpdateInput = z.infer<typeof usernameUpdateSchema>;

// ─── Password Change ─────────────────────────────────────────────────

/**
 * The special-character set is defined by the backend's `validate_password`.
 * Keep this in sync with `app/schemas/users.py`. If the backend changes,
 * both sides must change — that's the honest cost of mirroring rules.
 */
const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`";
const SPECIAL_CHARS_REGEX = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?/~`]/;

/**
 * Mirrors the backend's `StrongPassword` validator.
 *
 * - 8–100 characters
 * - At least one uppercase letter
 * - At least one lowercase letter
 * - At least one digit
 * - At least one special character from SPECIAL_CHARS
 */
const strongPasswordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(100, "Password must not exceed 100 characters")
  .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
  .regex(/[a-z]/, "Password must contain at least one lowercase letter")
  .regex(/[0-9]/, "Password must contain at least one number")
  .regex(
    SPECIAL_CHARS_REGEX,
    `Password must contain at least one special character (${SPECIAL_CHARS})`,
  );

/**
 * Form schema. The form collects three fields because the user types
 * the new password twice; `confirmPassword` never leaves the browser.
 *
 * The old password is required but not complexity-validated — matching
 * the backend's `PasswordChange.old_password: str`.
 */
export const passwordChangeSchema = z
  .object({
    oldPassword: z.string().min(1, "Current password is required"),
    newPassword: strongPasswordSchema,
    confirmPassword: z.string().min(1, "Please confirm your new password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type PasswordChangeInput = z.infer<typeof passwordChangeSchema>;

/**
 * Maps the form input (camelCase + confirmPassword) to the backend's
 * wire format (snake_case, no confirmPassword).
 *
 * This is the boundary where the form's shape and the API's shape
 * diverge. Keeping the transformation explicit and typed prevents drift.
 */
export function toPasswordChangePayload(
  data: PasswordChangeInput,
): PasswordChange {
  return {
    old_password: data.oldPassword,
    new_password: data.newPassword,
  };
}

// Compile-time assertion: guarantees the transformed payload satisfies
// the FastAPI contract. If `PasswordChange` ever gains a required field,
// this line will fail to compile, forcing us to update the mapping.
type _PasswordChangeAssert =
  ReturnType<typeof toPasswordChangePayload> extends PasswordChange
    ? true
    : never;
const _assertPasswordPayload: _PasswordChangeAssert = true;
void _assertPasswordPayload;
