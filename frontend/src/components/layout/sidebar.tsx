import { Nav } from "./nav";
import { FileText } from "lucide-react";

export function Sidebar() {
  return (
    <aside className="hidden lg:flex-col lg:flex w-64 shrink-0 border-r bg-sidebar">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <FileText className="h-6 w-6 text-primary" />
        <span className="font-semibold text-sidebar-foreground">Reviewer</span>
      </div>
      <Nav />
    </aside>
  );
}
