import { formatPrice } from "@/lib/utils";

export function OrderSummaryCard({ subtotal, shipping = 0, currency = "VND" }: { subtotal: number; shipping?: number; currency?: string }) {
  const total = subtotal + shipping;
  return <div className="rounded-2xl border border-border bg-white p-5"><h3 className="font-semibold">Tóm tắt đơn hàng</h3><div className="mt-4 space-y-2 text-sm"><div className="flex justify-between"><span>Tạm tính</span><span>{formatPrice(subtotal, currency)}</span></div><div className="flex justify-between"><span>Vận chuyển</span><span>{formatPrice(shipping, currency)}</span></div><div className="flex justify-between border-t border-border pt-2 text-base font-bold"><span>Tổng</span><span>{formatPrice(total, currency)}</span></div></div></div>;
}
