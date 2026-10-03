// src/features/users/schemas.ts
import { z } from "zod";
import type { PasswordChange, Role, UserCreate, UserUpdate } from "@/types";

// ─── Shared Field Primitives ─────────────────────────────────────────

const usernameSchema = z
  .string()
  .min(3, "Username must be at least 3 characters")
  .max(50, "Username must not exceed 50 characters");

/**
 * The special-character set mirrors `validate_password` in the backend's
 * `app/schemas/users.py`. If the backend changes its rules, this must change
 * in lockstep — the frontend is a friendly mirror, not the security boundary.
 */
const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`";
const SPECIAL_CHARS_REGEX = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?/~`]/;

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

const roleSchema = z.enum(["admin", "user", "viewer"] satisfies [
  Role,
  ...Role[],
]);

// ─── Self-service: Username Update ───────────────────────────────────

export const usernameUpdateSchema = z.object({
  username: usernameSchema,
});

export type UsernameUpdateInput = z.infer<typeof usernameUpdateSchema>;

// ─── Self-service: Password Change ───────────────────────────────────

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

export function toPasswordChangePayload(
  data: PasswordChangeInput,
): PasswordChange {
  return {
    old_password: data.oldPassword,
    new_password: data.newPassword,
  };
}

// ─── Admin: User Create ──────────────────────────────────────────────

export const userCreateSchema = z.object({
  username: usernameSchema,
  password: strongPasswordSchema,
  role: roleSchema,
});

export type UserCreateInput = z.infer<typeof userCreateSchema>;

export function toUserCreatePayload(data: UserCreateInput): UserCreate {
  return {
    username: data.username,
    password: data.password,
    role: data.role,
  };
}

type _UserCreateAssert =
  ReturnType<typeof toUserCreatePayload> extends UserCreate ? true : never;
const _assertUserCreate: _UserCreateAssert = true;
void _assertUserCreate;

// ─── Admin: User Update ──────────────────────────────────────────────

export const userUpdateSchema = z.object({
  username: usernameSchema,
  role: roleSchema,
  is_active: z.boolean(),
});

export type UserUpdateInput = z.infer<typeof userUpdateSchema>;

export function toUserUpdatePayload(data: UserUpdateInput): UserUpdate {
  return {
    username: data.username,
    role: data.role,
    is_active: data.is_active,
  };
}

type _UserUpdateAssert =
  ReturnType<typeof toUserUpdatePayload> extends UserUpdate ? true : never;
const _assertUserUpdate: _UserUpdateAssert = true;
void _assertUserUpdate;

// ─── Admin: Password Reset ───────────────────────────────────────────

/**
 * NOTE: The backend's admin password reset endpoint
 * (`POST /users/{user_id}/password`) reuses the `PasswordChange` schema
 * from the self-service flow, which means `old_password` is technically
 * required — even though an admin typically doesn't know the user's
 * current password.
 *
 * This is a backend design quirk. Two options:
 *   1. Ship this as-is and let the admin enter the target's current password.
 *   2. Update the backend to make `old_password` optional for admin resets,
 *      then remove the field from this schema.
 *
 * The frontend below assumes option 1 for correctness against the current API.
 */
export const adminPasswordResetSchema = z
  .object({
    oldPassword: z
      .string()
      .min(1, "The user's current password is required by the backend"),
    newPassword: strongPasswordSchema,
    confirmPassword: z.string().min(1, "Please confirm the new password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type AdminPasswordResetInput = z.infer<typeof adminPasswordResetSchema>;

export function toAdminPasswordResetPayload(
  data: AdminPasswordResetInput,
): PasswordChange {
  return {
    old_password: data.oldPassword,
    new_password: data.newPassword,
  };
}
