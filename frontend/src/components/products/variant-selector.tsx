"use client";

export function VariantSelector({ variants, value, onChange }: { variants: Array<{ id: string; name: string }>; value?: string; onChange: (id: string) => void }) {
  if (!variants?.length) return null;
  return <div className="flex flex-wrap gap-2">{variants.map((v) => <button key={v.id} onClick={() => onChange(v.id)} className={`rounded-full border px-3 py-1 text-sm ${value === v.id ? "border-slate-900 bg-slate-900 text-white" : "border-border bg-white"}`}>{v.name}</button>)}</div>;
}
