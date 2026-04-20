"use client";

import { QuantitySelector } from "@/components/cart/quantity-selector";
import { formatPrice } from "@/lib/utils";
import { getProductImageUrl } from "@/lib/product-image";

export function CartItemRow({ item, onQuantity, onRemove }: { item: { id: string; product_name: string; quantity: number; line_total: number; unit_price: number; thumbnail_url?: string }; onQuantity: (id: string, quantity: number) => void; onRemove: (id: string) => void }) {
  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-border bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <img
          src={getProductImageUrl({ name: item.product_name, thumbnail_url: item.thumbnail_url })}
          alt={item.product_name}
          className="h-16 w-16 rounded-2xl object-cover"
        />
        <div>
          <p className="font-semibold text-slate-950">{item.product_name}</p>
          <p className="text-sm text-slate-500">{formatPrice(item.unit_price)}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <QuantitySelector value={item.quantity} onChange={(v) => onQuantity(item.id, v)} />
        <p className="min-w-28 text-right font-bold text-slate-950">{formatPrice(item.line_total)}</p>
        <button onClick={() => onRemove(item.id)} className="text-sm font-semibold text-danger">
          Xoá
        </button>
      </div>
    </div>
  );
}
