const ACCESS = "techshop_access";
const REFRESH = "techshop_refresh";

export function setAuth(access: string, refresh?: string) {
  document.cookie = `${ACCESS}=${access}; path=/; max-age=86400; samesite=lax`;
  if (refresh) localStorage.setItem(REFRESH, refresh);
}

export function getAccessToken() {
  if (typeof document === "undefined") return "";
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${ACCESS}=`))
    ?.split("=")[1];
  return token ?? "";
}

export function getRefreshToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(REFRESH) ?? "";
}

export function clearAuth() {
  if (typeof document !== "undefined") {
    document.cookie = `${ACCESS}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }
  if (typeof window !== "undefined") {
    localStorage.removeItem(REFRESH);
  }
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}
