import { apiFetch } from "@/services/api/client";

export const getShipment = (reference: string) => apiFetch<{ shipment_reference: string; status: string; tracking_number?: string; tracking_url?: string }>(`/shipping/api/v1/shipments/${reference}/`);
export const getShipmentTracking = (reference: string) => apiFetch<{ status: string; timeline: Array<{ status: string; timestamp: string; location?: string }> }>(`/shipping/api/v1/shipments/${reference}/tracking/`);
