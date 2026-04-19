"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getOrderDetail, getOrderTimeline } from "@/services/api/orders";
import { getShipmentTracking } from "@/services/api/shipping";
import { mockPayFail, mockPaySuccess } from "@/services/api/payment";
import { StatusBadge } from "@/components/orders/status-badge";
import { TrackingTimeline } from "@/components/orders/tracking-timeline";
import { RecommendationCarousel } from "@/components/recommendations/recommendation-carousel";
import { getProducts } from "@/services/api/products";

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const justPlaced = search.get("justPlaced") === "1";
  const qc = useQueryClient();
  const { data: order } = useQuery({ queryKey: ["order", id], queryFn: () => getOrderDetail(id) });
  const { data: timeline } = useQuery({ queryKey: ["timeline", id], queryFn: () => getOrderTimeline(id), enabled: Boolean(order) });
  const { data: tracking } = useQuery({ queryKey: ["tracking", order?.shipment_reference], queryFn: () => getShipmentTracking(String(order?.shipment_reference)), enabled: Boolean(order?.shipment_reference) });
  const { data: rec } = useQuery({ queryKey: ["order-recommend"], queryFn: () => getProducts({ page_size: "3", is_featured: "true" }) });
  const paySuccess = useMutation({ mutationFn: (paymentReference: string) => mockPaySuccess(paymentReference), onSuccess: () => qc.invalidateQueries({ queryKey: ["order", id] }) });
  const payFail = useMutation({ mutationFn: (paymentReference: string) => mockPayFail(paymentReference), onSuccess: () => qc.invalidateQueries({ queryKey: ["order", id] }) });

  if (!order) return null;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-border bg-white p-5">
        {justPlaced ? <p className="mb-2 text-sm font-semibold text-emerald-700">Don hang da tao thanh cong.</p> : null}
        <h1 className="text-2xl font-bold">{order.order_number}</h1>
        <div className="mt-3 flex flex-wrap gap-2"><StatusBadge status={order.status} /><StatusBadge status={order.payment_status} /><StatusBadge status={order.fulfillment_status} /></div>
        <div className="mt-4 flex gap-2">
          <button onClick={() => order.payment_reference && paySuccess.mutate(order.payment_reference)} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white">Mock Pay Success</button>
          <button onClick={() => order.payment_reference && payFail.mutate(order.payment_reference)} className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white">Mock Pay Fail</button>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-white p-5">
        <h2 className="mb-4 text-xl font-bold">Timeline</h2>
        <TrackingTimeline items={timeline?.status_history ?? []} />
      </section>

      {(tracking as { events?: Array<{ status_after: string; event_time?: string; location?: string; description?: string }> })?.events?.length ? (
        <section className="rounded-2xl border border-border bg-white p-5">
          <h2 className="mb-3 text-xl font-bold">Shipment tracking</h2>
          <TrackingTimeline
            items={((tracking as { events?: Array<{ status_after: string; event_time?: string; location?: string; description?: string }> }).events ?? []).map((t) => ({
              to_status: t.status_after,
              created_at: t.event_time,
              note: t.location || t.description,
            }))}
          />
        </section>
      ) : null}

      <RecommendationCarousel products={rec?.results ?? []} title="Ban co the thich" />
    </div>
  );
}
