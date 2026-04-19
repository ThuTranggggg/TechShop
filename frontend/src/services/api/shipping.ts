import { apiFetch } from "@/services/api/client";

export const getShipment = (reference: string) => apiFetch<{ shipment_reference: string; status: string; tracking_number?: string; tracking_url?: string }>(`/shipping/api/v1/shipments/${reference}/`);
export const getShipmentTracking = (reference: string) =>
  apiFetch<{ status: string; events: Array<{ status_after: string; event_time: string; location?: string; description?: string }> }>(`/shipping/api/v1/shipments/${reference}/tracking/`);
export const getShipmentByOrder = (orderId: string) =>
  apiFetch<Record<string, unknown>>(`/shipping/api/v1/operations/shipments/order/${orderId}/`);
export const updateShipmentByOrder = (orderId: string, payload: { status: "pending" | "preparing" | "in_transit" | "delivered" | "returned"; location?: string; reason?: string }) =>
  apiFetch<Record<string, unknown>>(`/shipping/api/v1/operations/shipments/order/${orderId}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
