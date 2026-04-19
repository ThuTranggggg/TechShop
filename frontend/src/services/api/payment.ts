import { apiFetch } from "@/services/api/client";

export const getPaymentStatus = (reference: string) => apiFetch<{ status: string }>(`/payment/api/v1/payments/${reference}/status/`);
export const mockPaySuccess = (paymentReference: string) =>
  apiFetch<{ message: string }>("/payment/api/v1/webhooks/mock/", {
    method: "POST",
    body: JSON.stringify({ payment_reference: paymentReference, status: "completed" }),
  });
export const mockPayFail = (paymentReference: string) =>
  apiFetch<{ message: string }>("/payment/api/v1/webhooks/mock/", {
    method: "POST",
    body: JSON.stringify({ payment_reference: paymentReference, status: "failed" }),
  });
