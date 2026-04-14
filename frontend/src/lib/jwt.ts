type JwtPayload = {
  user_id?: string;
  sub?: string;
  exp?: number;
  [key: string]: unknown;
};

function base64UrlDecode(input: string) {
  const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  return atob(`${normalized}${padding}`);
}

export function decodeJwt(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    return JSON.parse(base64UrlDecode(parts[1])) as JwtPayload;
  } catch {
    return null;
  }
}

export function extractUserIdFromJwt(token: string) {
  const payload = decodeJwt(token);
  return (payload?.user_id ?? payload?.sub ?? "") as string;
}

export function extractUserRoleFromJwt(token: string) {
  const payload = decodeJwt(token);
  return (payload?.role ?? "") as string;
}
