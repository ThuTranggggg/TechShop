"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getOrders } from "@/services/api/orders";
import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/orders/status-badge";
import { formatPrice } from "@/lib/utils";

export default function OrdersPage() {
  const { data } = useQuery({ queryKey: ["orders"], queryFn: getOrders });
  if (!data?.length) return <EmptyState title="Bạn chưa có đơn hàng" description="Mua sắm và quay lại để xem lịch sử đơn hàng." />;

  return (
    <div className="space-y-3">
      {data.map((order) => (
        <article key={order.id} className="rounded-2xl border border-border bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-semibold">{order.order_number}</h3>
              <p className="text-sm text-slate-500">{formatPrice(Number(order.totals?.grand_total ?? 0), order.totals?.currency || "VND")}</p>
            </div>
            <StatusBadge status={order.status} />
          </div>
          <Link href={`/orders/${order.id}`} className="mt-3 inline-block text-sm font-semibold text-primary">Xem chi tiết</Link>
        </article>
      ))}
    </div>
  );
}
