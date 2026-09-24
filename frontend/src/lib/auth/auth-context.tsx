import { createContext } from "react";
import type { UserDetailed } from "@/types";

export type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  user: UserDetailed | null;
  status: AuthStatus;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
