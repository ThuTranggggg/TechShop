export function PriceBadge({ value, currency = "VND" }: { value: number; currency?: string }) {
  return <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-bold text-primary">{new Intl.NumberFormat("vi-VN", { style: "currency", currency, maximumFractionDigits: 0 }).format(value)}</span>;
}
