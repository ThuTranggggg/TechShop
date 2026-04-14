import { cn } from "@/lib/utils";
import { ReactNode } from "react";

export function FeatureCard({ title, description, icon, className }: { title: string; description: string; icon: ReactNode; className?: string }) {
  return (
    <article className={cn("rounded-2xl border border-border bg-white p-5 shadow-card", className)}>
      <div className="mb-3 inline-flex rounded-xl bg-slate-100 p-2">{icon}</div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
    </article>
  );
}
