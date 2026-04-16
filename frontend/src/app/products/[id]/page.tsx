"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getProductDetail } from "@/services/api/products";
import { addCartItem } from "@/services/api/cart";
import { VariantSelector } from "@/components/products/variant-selector";
import { ProductCard } from "@/components/products/product-card";
import { getProducts } from "@/services/api/products";
import { trackAiEvent } from "@/services/api/ai";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";
import { useMounted } from "@/hooks/use-mounted";

import { Check, ShieldCheck, Sparkles, Truck } from "lucide-react";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const mounted = useMounted();
  const token = getAccessToken();
  const userId = mounted && token ? extractUserIdFromJwt(token) : undefined;
  const [variantId, setVariantId] = useState<string>();
  const { data } = useQuery({ queryKey: ["product", id], queryFn: () => getProductDetail(id), enabled: Boolean(id) });
  const { data: relatedData } = useQuery({ queryKey: ["related", data?.category], enabled: Boolean(mounted && data), queryFn: () => getProducts({ category: String(data?.category), page_size: "3" }) });
  const addMutation = useMutation({
    mutationFn: addCartItem,
    onSuccess: () => {
      if (data) {
        trackAiEvent({
          event_type: "add_to_cart",
          user_id: userId,
          product_id: data.id,
          brand_name: data.brand_name,
          category_name: data.category_name,
          price_amount: Number(data.base_price),
        }).catch(() => undefined);
      }
      router.push("/cart");
    },
  });

  const variants = useMemo(() => (data?.variants ?? []).map((v) => ({ id: v.id, name: v.name })), [data?.variants]);
  const galleryImages = useMemo(() => {
    const mediaImages = (data?.media ?? []).map((item) => ({ src: item.media_url, alt: item.alt_text || data?.name || "Product image" }));
    const fallback = data?.thumbnail_url ? [{ src: data.thumbnail_url, alt: data.name }] : [];
    return [...mediaImages, ...fallback].slice(0, 5);
  }, [data]);
  useEffect(() => {
    if (!data) return;
    trackAiEvent({
      event_type: "product_view",
      user_id: userId,
      product_id: data.id,
      brand_name: data.brand_name,
      category_name: data.category_name,
      price_amount: Number(data.base_price),
    }).catch(() => undefined);
  }, [data, userId]);
  if (!data) return null;

  const formattedPrice = new Intl.NumberFormat("vi-VN").format(Number(data.base_price));

  return (
    <div className="space-y-16 pb-20">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:items-start">
        <div className="sticky top-24 space-y-4">
          <div className="overflow-hidden rounded-[2.5rem] bg-slate-50 card-premium">
            <img
              src={galleryImages[0]?.src || data.thumbnail_url || "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?w=1200"}
              alt={galleryImages[0]?.alt || data.name}
              className="aspect-square w-full object-cover transition-transform duration-700 hover:scale-105"
            />
          </div>
          <div className="grid grid-cols-4 gap-4">
            {galleryImages.slice(1, 5).map((image, index) => (
              <button
                key={`${image.src}-${index}`}
                type="button"
                className="overflow-hidden rounded-2xl border border-slate-200/50 bg-slate-100 transition-colors hover:border-primary"
              >
                <img src={image.src} alt={image.alt} className="aspect-square h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </div>

        {/* Product Info */}
        <div className="flex flex-col pt-4">
          <div className="mb-6 flex items-center gap-3">
            <span className="rounded-full bg-slate-100 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-slate-500">
              {data.brand_name}
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-sm font-medium text-slate-400">{data.category_name}</span>
          </div>

          <h1 className="text-4xl font-black tracking-tight text-slate-950 md:text-5xl lg:leading-[1.1]">
            {data.name}
          </h1>
          
          <div className="mt-8 flex items-baseline gap-4">
            <span className="text-4xl font-black text-slate-950">{formattedPrice} đ</span>
            <span className="text-lg font-medium text-slate-400 line-through">
              {new Intl.NumberFormat("vi-VN").format(Number(data.base_price) * 1.2)} đ
            </span>
          </div>

          <div className="mt-10 space-y-6 border-y border-slate-100 py-10">
            <div>
              <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-slate-900">Mô tả sản phẩm</h3>
              <p className="text-lg leading-relaxed text-slate-600">
                {data.description || data.short_description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-start gap-3 rounded-2xl bg-success/5 p-4">
                <ShieldCheck className="mt-0.5 h-5 w-5 text-success" />
                <div>
                  <div className="text-sm font-bold text-success">Bảo hành 12 tháng</div>
                  <div className="text-xs text-success/70">Chính hãng 100%</div>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-2xl bg-primary/5 p-4">
                <Truck className="mt-0.5 h-5 w-5 text-primary" />
                <div>
                  <div className="text-sm font-bold text-primary">Giao hàng hỏa tốc</div>
                  <div className="text-xs text-primary/70">Miễn phí toàn quốc</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-10 space-y-8">
            <VariantSelector variants={variants} value={variantId} onChange={setVariantId} />
            
            <div className="flex flex-col gap-4 sm:flex-row">
              <button 
                onClick={() => addMutation.mutate({ product_id: data.id, variant_id: variantId, quantity: 1 })}
                disabled={addMutation.isPending}
                className="btn-primary flex h-16 flex-1 items-center justify-center gap-3 text-lg"
              >
                <Sparkles className="h-5 w-5" />
                {addMutation.isPending ? "Đang xử lý..." : "Thêm vào giỏ hàng"}
              </button>
              <button
                onClick={() => addMutation.mutate({ product_id: data.id, variant_id: variantId, quantity: 1 })}
                disabled={addMutation.isPending}
                className="flex h-16 items-center justify-center rounded-[2rem] border-2 border-slate-950 px-10 text-lg font-bold transition-all hover:bg-slate-950 hover:text-white disabled:opacity-70"
              >
                Mua ngay
              </button>
            </div>
          </div>

          <div className="mt-12 flex items-center gap-8 text-sm font-medium text-slate-400">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-success" /> {data.status === "active" ? "Sẵn hàng giao nhanh" : "Cần xác nhận tồn kho"}
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-success" /> Hỗ trợ 24/7
            </div>
          </div>
        </div>
      </div>

      {/* Related Products */}
      <section className="border-t border-slate-100 pt-16">
        <header className="mb-12">
          <h2 className="text-3xl font-black">Sản phẩm liên quan</h2>
          <p className="mt-2 text-slate-500">Các mẫu cùng phân khúc hoặc cùng thương hiệu để bạn tham khảo.</p>
        </header>
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
           {relatedData?.results?.map((p) => (
              <ProductCard key={p.id} product={p} />
           ))}
        </div>
      </section>
    </div>
  );
}
