"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getCurrentCart, removeCartItem, updateCartItem } from "@/services/api/cart";
import { CartItemRow } from "@/components/cart/cart-item-row";
import { EmptyState } from "@/components/ui/empty-state";
import { OrderSummaryCard } from "@/components/orders/order-summary-card";
import Link from "next/link";

import { ArrowRight, ShoppingBag, Sparkles } from "lucide-react";

export default function CartPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["cart"], queryFn: getCurrentCart });
  const updateMutation = useMutation({ mutationFn: ({ id, quantity }: { id: string; quantity: number }) => updateCartItem(id, quantity), onSuccess: () => qc.invalidateQueries({ queryKey: ["cart"] }) });
  const removeMutation = useMutation({ mutationFn: removeCartItem, onSuccess: () => qc.invalidateQueries({ queryKey: ["cart"] }) });

  if (!data?.items?.length) return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <div className="mb-8 flex h-24 w-24 items-center justify-center rounded-full bg-slate-50 text-slate-300">
        <ShoppingBag className="h-12 w-12" />
      </div>
      <h2 className="text-3xl font-black text-slate-950">Giỏ hàng của bạn đang trống</h2>
      <p className="mt-4 max-w-sm text-lg text-slate-500">
        Đừng bỏ lỡ các ưu đãi hấp dẫn. Khám phá những sản phẩm công nghệ mới nhất ngay bây giờ!
      </p>
      <Link href="/" className="btn-primary mt-10 px-10 h-14">
        Tiếp tục mua hàng
      </Link>
    </div>
  );

  return (
    <div className="pb-20">
      <header className="mb-12 border-b border-slate-100 pb-10">
        <h1 className="text-4xl font-black tracking-tight text-slate-950">Giỏ hàng của bạn.</h1>
        <p className="mt-2 text-lg text-slate-500">Bạn đang có {data.items.length} sản phẩm trong giỏ hàng.</p>
      </header>

      <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:items-start">
        <div className="space-y-6 lg:col-span-8">
          {data.items.map((item) => (
            <div key={item.id} className="card-premium group relative bg-white p-6">
              <CartItemRow 
                item={item} 
                onQuantity={(id, quantity) => updateMutation.mutate({ id, quantity })} 
                onRemove={(id) => removeMutation.mutate(id)} 
              />
            </div>
          ))}

          <div className="mt-12 flex flex-col items-center justify-between gap-6 overflow-hidden rounded-[2rem] bg-slate-950 p-8 text-white sm:flex-row">
            <div className="flex items-center gap-6">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10">
                <Sparkles className="h-7 w-7 text-primary" />
              </div>
              <div>
                <div className="text-lg font-bold">Ưu đãi thành viên</div>
                <div className="text-sm text-slate-400">Đăng nhập để nhận thêm mã giảm giá hỏa tốc</div>
              </div>
            </div>
            <Link href="/login" className="flex items-center gap-2 font-bold text-white hover:text-primary transition-colors">
              Đăng nhập ngay <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <aside className="lg:sticky lg:top-24 lg:col-span-4">
          <div className="card-premium bg-slate-50/50 p-8 backdrop-blur-xl">
             <OrderSummaryCard subtotal={Number(data.subtotal_amount)} currency={data.currency} />
             <Link 
              href="/checkout" 
              className="btn-primary mt-8 flex h-14 w-full items-center justify-center gap-3"
            >
              Tiến hành thanh toán <ArrowRight className="h-5 w-5" />
            </Link>
            <p className="mt-6 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">
              An toàn & Bảo mật 100%
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
