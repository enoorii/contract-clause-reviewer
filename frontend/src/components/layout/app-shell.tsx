// src/app/App.tsx
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { MOCK_USER } from "@/lib/mock-data";
import { Outlet } from "react-router";

export default function AppShell() {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header user={MOCK_USER} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
