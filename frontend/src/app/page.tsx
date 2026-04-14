"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowRight, Bot, ShieldCheck, Sparkles, Truck } from "lucide-react";
import Link from "next/link";
import { SearchBar } from "@/components/products/search-bar";
import { ProductCard } from "@/components/products/product-card";
import { SectionHeader } from "@/components/ui/section-header";
import { getProducts } from "@/services/api/products";
import { getRecommendations } from "@/services/api/ai";

export default function HomePage() {
  const router = useRouter();
  const { data: productsData } = useQuery({
    queryKey: ["home-products"],
    queryFn: () => getProducts({ page_size: "8" }),
  });

  const products = productsData?.results ?? [];

  const { data: recData } = useQuery({
    queryKey: ["home-recommendations", products.length],
    enabled: products.length > 0,
    queryFn: () =>
      getRecommendations({
        products: products.map((p) => ({
          id: p.id,
          name: p.name,
          brand: p.brand_name,
          category: p.category_name,
          price: p.base_price,
          thumbnail_url: p.thumbnail_url,
        })),
        limit: 4,
      }),
  });

  return (
    <div className="space-y-14 pb-10">
      <section className="relative overflow-hidden rounded-[2.5rem] border border-border/80 bg-gradient-to-br from-orange-50 via-white to-emerald-50 p-7 md:p-12">
        <div className="pointer-events-none absolute -right-24 top-0 h-64 w-64 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-accent/20 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Techshop 2026
            </span>
            <h1 className="mt-6 text-4xl font-black leading-tight text-slate-900 md:text-6xl">
              Mua sắm công nghệ
              <br />
              theo cách hoàn toàn mới.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-slate-600">
              Một không gian mua sắm tập trung vào tốc độ, minh bạch tồn kho và AI hỗ trợ tìm sản phẩm theo nhu cầu thật.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button onClick={() => router.push("/products")} className="btn-primary h-12 px-7">
                Khám phá sản phẩm
              </button>
              <button onClick={() => router.push("/chat")} className="btn-secondary h-12 px-7">
                Chat với AI
              </button>
            </div>
            <div className="mt-8 max-w-2xl">
              <SearchBar onSubmit={(q) => router.push(`/products?search=${encodeURIComponent(q)}`)} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <article className="card-premium bg-white/80">
              <ShieldCheck className="h-6 w-6 text-primary" />
              <h3 className="mt-4 font-display text-xl font-bold">Bảo mật mua hàng</h3>
              <p className="mt-2 text-sm text-slate-600">Luồng thanh toán được kiểm soát và đồng bộ trạng thái giữa các service.</p>
            </article>
            <article className="card-premium bg-white/80">
              <Truck className="h-6 w-6 text-accent" />
              <h3 className="mt-4 font-display text-xl font-bold">Giao vận rõ ràng</h3>
              <p className="mt-2 text-sm text-slate-600">Theo dõi hành trình đơn hàng chi tiết, cập nhật liên tục theo timeline.</p>
            </article>
            <article className="card-premium bg-white/80 sm:col-span-2 lg:col-span-1">
              <Bot className="h-6 w-6 text-warning" />
              <h3 className="mt-4 font-display text-xl font-bold">AI tư vấn nhanh</h3>
              <p className="mt-2 text-sm text-slate-600">Gợi ý sản phẩm theo ngân sách, thương hiệu và mục đích sử dụng ngay trong chat.</p>
            </article>
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          title="Sản phẩm nổi bật"
          subtitle="Bộ sưu tập thiết bị được chọn lọc cho trải nghiệm mua sắm thử nghiệm toàn diện."
        />
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </section>

      {recData?.products?.length ? (
        <section className="rounded-[2.5rem] border border-border/80 bg-card p-7 md:p-10">
          <SectionHeader
            title="Gợi ý AI cho bạn"
            subtitle="Từ hành vi xem sản phẩm, hệ thống đề xuất những lựa chọn tiệm cận nhất với nhu cầu."
          />
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {recData.products.map((item) => (
              <article key={item.product_id} className="rounded-2xl border border-border bg-muted/40 p-4">
                <div className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                  {item.reason_codes?.[0] ?? "Recommendation"}
                </div>
                <h3 className="mt-3 line-clamp-2 font-display text-lg font-bold text-slate-900">{item.product_name}</h3>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">{item.brand}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">
                    {new Intl.NumberFormat("vi-VN").format(Number(item.price))} đ
                  </span>
                  <Link href={`/products/${item.product_id}`} className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white">
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
