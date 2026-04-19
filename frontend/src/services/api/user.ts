import { apiFetch } from "@/services/api/client";

export const login = (payload: { email: string; password: string }) =>
  apiFetch<{ access: string; refresh: string; user: { id: string; email: string; full_name: string; role?: string } }>("/user/api/v1/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const register = (payload: { email: string; full_name: string; password: string; password_confirm: string; phone_number?: string }) =>
  apiFetch<{ id: string; email: string; full_name: string; role?: string }>("/user/api/v1/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const me = () => apiFetch<{ id: string; email: string; full_name: string; role?: string }>("/user/api/v1/auth/me/");
export const getAddresses = () => apiFetch<Array<{ id: string; receiver_name: string; phone_number: string; line1: string; district: string; city: string; country: string; is_default: boolean }>>("/user/api/v1/profile/addresses/");
