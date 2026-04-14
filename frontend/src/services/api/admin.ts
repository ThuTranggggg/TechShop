import { apiFetch } from "@/services/api/client";
import { Product } from "@/types/models";

export const adminListProducts = () =>
  apiFetch<{ count: number; results: Product[] }>("/product/api/v1/catalog/admin/products/");

export const adminCreateProduct = (payload: Record<string, unknown>) =>
  apiFetch<Product>("/product/api/v1/catalog/admin/products/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const adminUpdateProduct = (id: string, payload: Record<string, unknown>) =>
  apiFetch<Product>(`/product/api/v1/catalog/admin/products/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const adminDeleteProduct = (id: string) =>
  apiFetch<{ message?: string }>(`/product/api/v1/catalog/admin/products/${id}/`, {
    method: "DELETE",
  });
