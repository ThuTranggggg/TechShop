"use client";

import Link from "next/link";
import { Compass, LayoutDashboard, LogOut, Sparkles, UserCircle2 } from "lucide-react";
import { CartBadge } from "@/components/cart/cart-badge";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { clearAuth, getAccessToken } from "@/services/auth";
import { extractUserRoleFromJwt } from "@/lib/jwt";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { me } from "@/services/api/user";

const links = [
  { href: "/products", label: "Sản phẩm" },
  { href: "/orders", label: "Đơn hàng" },
  { href: "/chat", label: "Demo AI" },
];

export function AppHeader() {
  const pathname = usePathname();
  const token = getAccessToken();
  const role = useMemo(() => (token ? extractUserRoleFromJwt(token) : ""), [token]);
  const isAdmin = role === "admin" || role === "staff";
  const { data: profile } = useQuery({ queryKey: ["me"], queryFn: me, enabled: Boolean(token) });

  return (
    <header className="sticky top-0 z-50 glass">
      <div className="container-app flex h-20 items-center justify-between gap-4">
        <Link href="/" className="group flex items-center gap-3 transition-all">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-white shadow-card transition-all group-hover:scale-105">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="hidden sm:block">
            <div className="font-display text-xl font-extrabold tracking-tight">TechShop</div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Trải nghiệm thương mại AI</div>
          </div>
        </Link>
        <nav className="hidden lg:flex items-center gap-3 rounded-full border border-border/80 bg-card/70 p-1.5 text-sm font-bold shadow-soft">
          {links.map((link) => (
            <Link 
              key={link.href} 
              href={link.href} 
              prefetch={false}
              className={cn(
                "rounded-full px-4 py-2.5 transition-all",
                pathname.startsWith(link.href)
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-muted hover:text-slate-900"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          {isAdmin ? (
            <Link href="/admin" prefetch={false} className="hidden sm:inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-muted">
              <LayoutDashboard className="h-3.5 w-3.5" />
              Admin
            </Link>
          ) : null}
          <Link href="/products" className="hidden sm:inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-muted">
            <Compass className="h-3.5 w-3.5" />
            Khám phá
          </Link>
          <Link href="/chat" className="hidden md:inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-muted">
            <Sparkles className="h-3.5 w-3.5" />
            Demo RAG
          </Link>
          <Link href="/cart" prefetch={false} className="relative transition-transform hover:scale-110 active:scale-90" aria-label="Giỏ hàng">
            <CartBadge />
          </Link>
          {token ? (
            <div className="flex items-center gap-2">
              <Link href="/profile" prefetch={false} className="btn-primary py-2.5 shadow-soft">
                <UserCircle2 className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">{profile?.full_name || "Tài khoản"}</span>
              </Link>
              <button
                onClick={() => {
                  clearAuth();
                  window.location.href = "/login";
                }}
                className="inline-flex items-center rounded-full border border-border bg-card px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-muted"
                aria-label="Đăng xuất"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <Link href="/login" className="btn-primary py-2.5 shadow-soft">
              <UserCircle2 className="mr-2 h-4 w-4" />
              <span className="hidden sm:inline">Tài khoản</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
