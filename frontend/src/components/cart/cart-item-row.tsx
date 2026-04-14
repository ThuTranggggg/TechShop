"use client";

import { QuantitySelector } from "@/components/cart/quantity-selector";
import { formatPrice } from "@/lib/utils";

export function CartItemRow({ item, onQuantity, onRemove }: { item: { id: string; product_name: string; quantity: number; line_total: number; unit_price: number; thumbnail_url?: string }; onQuantity: (id: string, quantity: number) => void; onRemove: (id: string) => void }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <img src={item.thumbnail_url || "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?w=800"} alt={item.product_name} className="h-14 w-14 rounded-lg object-cover" />
        <div><p className="font-semibold">{item.product_name}</p><p className="text-sm text-slate-500">{formatPrice(item.unit_price)}</p></div>
      </div>
      <div className="flex items-center gap-3"><QuantitySelector value={item.quantity} onChange={(v) => onQuantity(item.id, v)} /><p className="min-w-28 text-right font-bold">{formatPrice(item.line_total)}</p><button onClick={() => onRemove(item.id)} className="text-sm text-danger">Xóa</button></div>
    </div>
  );
}
