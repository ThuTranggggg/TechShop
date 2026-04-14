export function StatusBadge({ status }: { status?: string }) {
  const normalized = (status ?? "unknown").toLowerCase();
  const tone = normalized.includes("deliver") || normalized.includes("complete") ? "bg-emerald-100 text-emerald-700" : normalized.includes("fail") || normalized.includes("cancel") ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700";
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>{status ?? "unknown"}</span>;
}
