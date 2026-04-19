import { config } from "@/lib/config";
import { extractUserIdFromJwt, extractUserRoleFromJwt } from "@/lib/jwt";
import { getAccessToken, clearAuth } from "@/services/auth";

type ApiResult<T> = { success: boolean; message?: string; data?: T; errors?: Record<string, unknown> };

function parseApiError(result: ApiResult<unknown>) {
  if (typeof result.errors === "string") return result.errors;
  if (Array.isArray(result.errors)) return result.errors.join(", ");
  if (result.errors && typeof result.errors === "object") {
    const first = Object.values(result.errors)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (typeof first === "string") return first;
  }
  return result.message ?? "Request failed";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token) {
    const userId = extractUserIdFromJwt(token);
    const role = extractUserRoleFromJwt(token);
    if (userId) headers.set("X-User-ID", userId);
    if (role) headers.set("X-User-Role", role);
    if (role === "admin" || role === "staff") headers.set("X-Admin", "true");
    if (path.startsWith("/user/")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const base = config.apiBaseUrl.endsWith("/") ? config.apiBaseUrl.slice(0, -1) : config.apiBaseUrl;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const response = await fetch(`${base}${normalizedPath}`, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const json = (contentType.includes("application/json")
    ? ((await response.json()) as ApiResult<T>)
    : ({ success: response.ok, message: await response.text() } as ApiResult<T>));

  if (!response.ok || json.success === false) {
    if (response.status === 401) clearAuth();
    throw new Error(parseApiError(json));
  }

  return (json.data as T) ?? (json as unknown as T);
}
