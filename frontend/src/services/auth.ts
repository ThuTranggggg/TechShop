const ACCESS = "techshop_access";
const REFRESH = "techshop_refresh";
const ACCESS_STORAGE = "techshop_access_storage";

function buildCookie(name: string, value: string, maxAge: number) {
  return `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Lax`;
}

export function setAuth(access: string, refresh?: string) {
  if (typeof document !== "undefined") {
    document.cookie = buildCookie(ACCESS, access, 86400);
  }
  if (typeof window !== "undefined") {
    localStorage.setItem(ACCESS_STORAGE, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  }
}

export function getAccessToken() {
  if (typeof document === "undefined") return "";
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${ACCESS}=`))
    ?.split("=")[1];
  return token ? decodeURIComponent(token) : "";
}

export function getRefreshToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(REFRESH) ?? "";
}

export function getStoredAccessToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(ACCESS_STORAGE) ?? "";
}

export function ensureAuthCookie() {
  if (typeof document === "undefined" || typeof window === "undefined") return "";
  const cookieToken = getAccessToken();
  if (cookieToken) return cookieToken;

  const storedToken = getStoredAccessToken();
  if (storedToken) {
    document.cookie = buildCookie(ACCESS, storedToken, 86400);
    return storedToken;
  }

  return "";
}

export function clearAuth() {
  if (typeof document !== "undefined") {
    document.cookie = `${ACCESS}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`;
  }
  if (typeof window !== "undefined") {
    localStorage.removeItem(ACCESS_STORAGE);
    localStorage.removeItem(REFRESH);
  }
}

export function isAuthenticated() {
  return Boolean(getAccessToken() || getStoredAccessToken());
}
