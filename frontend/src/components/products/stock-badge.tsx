export function StockBadge({ status }: { status?: string }) {
  const inStock = !status || status.toLowerCase().includes("available") || status.toLowerCase().includes("active");
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${inStock ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>{inStock ? "Còn hàng" : "Hết hàng"}</span>;
}
