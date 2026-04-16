import { cn } from "@/lib/utils";

export function SectionHeader({ title, subtitle, className }: { title: string; subtitle?: string; className?: string }) {
  return (
    <div className={cn("mb-6", className)}>
      <h2 className="text-2xl font-bold text-slate-900 md:text-[2rem]">{title}</h2>
      {subtitle ? <p className="mt-1 max-w-2xl text-slate-600">{subtitle}</p> : null}
    </div>
  );
}
