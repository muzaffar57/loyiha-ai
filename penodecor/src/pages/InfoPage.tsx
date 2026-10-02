import type { ReactNode } from "react";
import { PageHeader } from "../components/PageHeader";

export function InfoPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="lg:pt-8">
      <PageHeader title={title} back />
      <article className="mt-2 max-w-2xl space-y-4 text-sm leading-7 text-ink">{children}</article>
    </div>
  );
}
