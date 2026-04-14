import { format } from "date-fns";

export function TrackingTimeline({ items }: { items: Array<{ to_status: string; created_at?: string; note?: string }> }) {
  return <div className="space-y-4">{items.map((it, idx) => <div key={`${it.to_status}-${idx}`} className="relative pl-6"><span className="absolute left-0 top-1 h-3 w-3 rounded-full bg-primary" /><p className="font-semibold capitalize">{it.to_status.replaceAll("_", " ")}</p><p className="text-xs text-slate-500">{it.created_at ? format(new Date(it.created_at), "dd/MM/yyyy HH:mm") : ""}</p>{it.note ? <p className="text-sm text-slate-600">{it.note}</p> : null}</div>)}</div>;
}
