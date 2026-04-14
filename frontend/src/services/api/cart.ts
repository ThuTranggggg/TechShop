import { apiFetch } from "@/services/api/client";
import { Cart } from "@/types/models";

export const getCurrentCart = () => apiFetch<Cart>("/cart/api/v1/cart/current/");
export const getCartSummary = () => apiFetch<{ item_count: number; total_quantity: number; subtotal_amount: number; currency: string }>("/cart/api/v1/cart/summary/");
export const addCartItem = (payload: { product_id: string; variant_id?: string; quantity: number }) =>
  apiFetch<Cart>("/cart/api/v1/cart/items/", { method: "POST", body: JSON.stringify(payload) });
export const updateCartItem = (itemId: string, quantity: number) =>
  apiFetch<Cart>(`/cart/api/v1/cart/items/${itemId}/quantity/`, { method: "PATCH", body: JSON.stringify({ new_quantity: quantity }) });
export const removeCartItem = (itemId: string) =>
  apiFetch<Cart>(`/cart/api/v1/cart/items/${itemId}/`, { method: "DELETE" });
export const clearCart = () => apiFetch<Cart>("/cart/api/v1/cart/clear/", { method: "POST" });
export const checkoutPreview = () => apiFetch<{ is_valid: boolean; issues: Array<{ message: string }>; cart: Cart }>("/cart/api/v1/cart/checkout-preview/", { method: "POST" });
