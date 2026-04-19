"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Product } from "@/types/models";
import { PriceBadge } from "@/components/products/price-badge";
import { BrandBadge } from "@/components/products/brand-badge";
import { StockBadge } from "@/components/products/stock-badge";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";
import { trackAiEvent } from "@/services/api/ai";

export function ProductCard({ product }: { product: Product }) {
  const formattedPrice = new Intl.NumberFormat("vi-VN").format(Number(product.base_price));
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const trackClick = () =>
    trackAiEvent({
      event_type: "product_click",
      user_id: userId,
      product_id: product.id,
      brand_name: product.brand_name,
      category_name: product.category_name,
      price_amount: Number(product.base_price),
    }).catch(() => undefined);
  
  return (
    <article className="group card-premium relative flex flex-col items-stretch overflow-hidden bg-card p-0">
      <Link href={`/products/${product.id}`} onClick={trackClick} className="relative block aspect-[4/3] w-full overflow-hidden bg-muted">
        <img 
          src={product.thumbnail_url || "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=900"} 
          alt={product.name} 
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110" 
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/35 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
        <div className="absolute left-4 top-4 flex flex-col gap-2">
          <BrandBadge name={product.brand_name} />
          <StockBadge status={product.status} />
        </div>
      </Link>
      
      <div className="flex flex-1 flex-col p-6">
        <Link href={`/products/${product.id}`} onClick={trackClick} className="group/title">
          <h3 className="line-clamp-2 min-h-[3rem] text-lg font-bold leading-snug group-hover/title:text-primary transition-colors">
            {product.name}
          </h3>
        </Link>
        
        <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-600">
          {product.short_description}
        </p>
        
        <div className="mt-8 flex items-center justify-between border-t border-border/60 pt-4">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Giá niêm yết</div>
            <div className="text-xl font-black text-slate-900">{formattedPrice} đ</div>
          </div>
          <Link 
            href={`/products/${product.id}`} 
            onClick={trackClick}
            aria-label={`Xem chi tiet san pham ${product.name}`}
            className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white transition-all hover:scale-105 hover:bg-primary"
          >
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}
