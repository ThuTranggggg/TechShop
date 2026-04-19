"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ensureAuthCookie, getStoredAccessToken } from "@/services/auth";

const protectedPaths = ["/cart", "/checkout", "/orders", "/chat", "/profile", "/admin"];

export function AuthBootstrap() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const restoredToken = ensureAuthCookie();
    if (restoredToken && protectedPaths.some((path) => pathname.startsWith(path))) {
      router.refresh();
      return;
    }

    const storedToken = getStoredAccessToken();
    if (!storedToken && pathname === "/login") {
      return;
    }
  }, [pathname, router]);

  return null;
}
