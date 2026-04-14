import { apiFetch } from "@/services/api/client";

export const getPaymentStatus = (reference: string) => apiFetch<{ status: string }>(`/payment/api/v1/payments/${reference}/status/`);
export const mockPaySuccess = () => apiFetch<{ message: string }>("/payment/api/v1/webhooks/mock/", { method: "POST", body: JSON.stringify({ status: "completed" }) });
export const mockPayFail = () => apiFetch<{ message: string }>("/payment/api/v1/webhooks/mock/", { method: "POST", body: JSON.stringify({ status: "failed" }) });
