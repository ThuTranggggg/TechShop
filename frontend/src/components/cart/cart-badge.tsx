"use client";

import { useQuery } from "@tanstack/react-query";
import { getCartSummary } from "@/services/api/cart";
import { ShoppingBag } from "lucide-react";
import { getAccessToken } from "@/services/auth";
import { useMounted } from "@/hooks/use-mounted";

export function CartBadge() {
  const mounted = useMounted();
  const token = getAccessToken();
  const { data } = useQuery({
    queryKey: ["cart-summary"],
    queryFn: getCartSummary,
    staleTime: 30000,
    enabled: mounted && Boolean(token),
  });
  const count = data?.item_count ?? 0;
  return (
    <span className="relative inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-white">
      <ShoppingBag className="h-4 w-4" />
      {count > 0 ? <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-primary px-1.5 text-center text-xs font-bold text-white">{count}</span> : null}
    </span>
  );
}
