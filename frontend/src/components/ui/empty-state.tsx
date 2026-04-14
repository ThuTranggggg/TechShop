export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="rounded-2xl border border-dashed border-border bg-white p-8 text-center"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-slate-600">{description}</p></div>;
}
