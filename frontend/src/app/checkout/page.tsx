"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { checkoutPreview, getCurrentCart } from "@/services/api/cart";
import { createOrderFromCart } from "@/services/api/orders";
import { AddressForm, AddressInput } from "@/components/ui/address-form";
import { OrderSummaryCard } from "@/components/orders/order-summary-card";
import { useRouter } from "next/navigation";
import { trackAiEvent } from "@/services/api/ai";
import { getAccessToken } from "@/services/auth";
import { decodeJwt, extractUserIdFromJwt } from "@/lib/jwt";
import { useMounted } from "@/hooks/use-mounted";

export default function CheckoutPage() {
  const router = useRouter();
  const mounted = useMounted();
  const token = getAccessToken();
  const tokenData = mounted && token ? decodeJwt(token) : null;
  const userId = mounted && token ? extractUserIdFromJwt(token) : undefined;
  const [error, setError] = useState("");
  const { data: cart } = useQuery({ queryKey: ["cart"], queryFn: getCurrentCart, enabled: mounted && Boolean(token) });
  useQuery({ queryKey: ["checkout-preview"], queryFn: checkoutPreview, enabled: mounted && Boolean(token) });
  useEffect(() => {
    trackAiEvent({ event_type: "checkout_started", user_id: userId, metadata: { source: "checkout_page" } }).catch(() => undefined);
  }, [userId]);

  const createMutation = useMutation({
    mutationFn: (shipping_address: AddressInput) => createOrderFromCart({
      cart_id: cart!.id,
      shipping_address,
      customer: tokenData ? {
        name: String(tokenData.full_name ?? ""),
        email: String(tokenData.email ?? ""),
      } : undefined,
    }),
    onSuccess: (order) => {
      trackAiEvent({ event_type: "order_created", user_id: userId, metadata: { order_id: order.id } }).catch(() => undefined);
      router.push(`/orders/${order.id}?justPlaced=1`);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "Checkout failed"),
  });

  if (!mounted || !cart) return null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
      <section className="rounded-2xl border border-border bg-white p-5">
        <h1 className="mb-4 text-2xl font-bold">Checkout</h1>
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <AddressForm loading={createMutation.isPending} onSubmit={(data) => createMutation.mutate(data)} />
      </section>
      <OrderSummaryCard subtotal={Number(cart.subtotal_amount)} currency={cart.currency} />
    </div>
  );
}
