import type { ReactNode } from "react";
import { BottomNav, DesktopNav } from "./BottomNav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <a href="#mazmun" className="skip-link">
        Mazmunga o‘tish
      </a>
      <DesktopNav />
      <div className="mx-auto min-h-dvh w-full max-w-lg bg-canvas lg:max-w-6xl">
        <main id="mazmun" className="shell-main px-4 pt-[var(--safe-top)] lg:px-8">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
