// src/features/users/components/users-filters.tsx
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Role } from "@/types";

interface UsersFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  role: Role | null;
  onRoleChange: (value: Role | null) => void;
  isActive: boolean | null;
  onIsActiveChange: (value: boolean | null) => void;
}

export function UsersFilters({
  search,
  onSearchChange,
  role,
  onRoleChange,
  isActive,
  onIsActiveChange,
}: UsersFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Input
        placeholder="Search by username..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="sm:max-w-xs"
      />

      <Select
        value={role ?? "all"}
        onValueChange={(v) => onRoleChange(v === "all" ? null : (v as Role))}
      >
        <SelectTrigger className="sm:w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All roles</SelectItem>
          <SelectItem value="admin">Admin</SelectItem>
          <SelectItem value="user">User</SelectItem>
          <SelectItem value="viewer">Viewer</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={isActive === null ? "all" : isActive ? "active" : "inactive"}
        onValueChange={(v) => {
          if (v === "all") onIsActiveChange(null);
          else onIsActiveChange(v === "active");
        }}
      >
        <SelectTrigger className="sm:w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="inactive">Inactive</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
