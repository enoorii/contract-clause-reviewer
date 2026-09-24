import { ThemeProvider as NextThemeProvider } from "next-themes";
import type { PropsWithChildren } from "react";
import { AuthProvider } from "@/lib/auth/auth-provider";

export function Providers({ children }: PropsWithChildren) {
  return (
    <NextThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <AuthProvider>{children}</AuthProvider>
    </NextThemeProvider>
  );
}
