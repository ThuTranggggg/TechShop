export function BrandBadge({ name }: { name?: string }) {
  return <span className="rounded-full bg-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700">{name ?? "Brand"}</span>;
}
