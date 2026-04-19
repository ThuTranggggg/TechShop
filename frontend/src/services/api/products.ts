import { apiFetch } from "@/services/api/client";
import { Product } from "@/types/models";

export async function getProducts(params: Record<string, string>) {
  const q = new URLSearchParams(params).toString();
  return apiFetch<{ count: number; next: string | null; previous: string | null; results: Product[] }>(`/product/api/v1/catalog/products/${q ? `?${q}` : ""}`);
}

export async function getProductDetail(id: string) {
  return apiFetch<Product>(`/product/api/v1/catalog/products/${id}/`);
}

export async function getProductVariants(id: string) {
  return apiFetch<Array<{ id: string; name: string; price_override?: number }>>(`/product/api/v1/catalog/products/${id}/variants/`);
}

export async function getCategories() {
  return apiFetch<{ results: Array<{ id: string; name: string; slug: string; children_count?: number; products_count?: number }> }>("/product/api/v1/catalog/categories/");
}

export async function getBrands() {
  return apiFetch<{ results: Array<{ id: string; name: string; slug: string }> }>("/product/api/v1/catalog/brands/");
}

export async function getProductTypes() {
  return apiFetch<{ results: Array<{ id: string; name: string; code?: string }> }>("/product/api/v1/catalog/product-types/");
}
