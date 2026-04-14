import { apiFetch } from "@/services/api/client";
import { Order } from "@/types/models";

export const createOrderFromCart = (payload: { cart_id: string; shipping_address: Record<string, string>; notes?: string }) =>
  apiFetch<Order>("/order/api/v1/orders/from-cart/", { method: "POST", body: JSON.stringify(payload) });

export const getOrders = () => apiFetch<Order[]>("/order/api/v1/orders/");
export const getOrderDetail = (id: string) => apiFetch<Order>(`/order/api/v1/orders/${id}/`);
export const getOrderTimeline = (id: string) =>
  apiFetch<{ status_history: Array<{ to_status: string; note?: string; created_at?: string }> }>(`/order/api/v1/orders/${id}/timeline/`);
