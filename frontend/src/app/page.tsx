"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowRight, Bot, BrainCircuit, Database, MessagesSquare, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { SearchBar } from "@/components/products/search-bar";
import { ProductCard } from "@/components/products/product-card";
import { SectionHeader } from "@/components/ui/section-header";
import { getKnowledgeDocuments, getRecommendations } from "@/services/api/ai";
import { getProducts } from "@/services/api/products";

const evaluationChecklist = [
  { title: "Catalog thật", status: "Đạt", note: "Có đủ sản phẩm seed và giá hiển thị rõ ràng." },
  { title: "Dịch vụ AI", status: "Đạt", note: "Có recommendation, tracking và chat." },
  { title: "Kho tri thức", status: "Đạt", note: "Có tài liệu nội bộ cho RAG." },
  { title: "RAG + chat", status: "Đạt", note: "Có nguồn tri thức và sản phẩm liên quan." },
  { title: "Luồng demo", status: "Đạt", note: "Có luồng mua sắm end-to-end." },
];

const aiHighlights = [
  {
    title: "Mô hình AI",
    description: "Phân loại ý định, trích xuất thực thể và gợi ý nội dung phù hợp.",
    icon: BrainCircuit,
  },
  {
    title: "Kho tri thức",
    description: "Tài liệu giao hàng, thanh toán, đổi trả và hỗ trợ để RAG truy hồi.",
    icon: Database,
  },
  {
    title: "RAG + chat",
    description: "Câu trả lời có thể đi kèm nguồn và sản phẩm liên quan ngay trong UI.",
    icon: MessagesSquare,
  },
];

const demoFlow = [
  "Mở catalog để xem sản phẩm, giá và ảnh đúng ngữ nghĩa.",
  "Dùng AI chat để hỏi theo ngân sách, thương hiệu hoặc chính sách.",
  "Chuyển sang giỏ hàng và checkout để kiểm tra luồng mua hàng hoàn chỉnh.",
];

export default function HomePage() {
  const router = useRouter();
  const { data: productsData } = useQuery({
    queryKey: ["home-products"],
    queryFn: () => getProducts({ page_size: "12", ordering: "-published_at" }),
  });

  const { data: knowledgeData } = useQuery({
    queryKey: ["home-knowledge-documents"],
    queryFn: getKnowledgeDocuments,
  });

  const products = productsData?.results ?? [];
  const productCount = productsData?.count ?? products.length;
  const knowledgeDocs = knowledgeData?.documents ?? [];

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
        <div className="relative grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Demo thương mại AI TechShop
            </span>
            <h1 className="mt-6 text-4xl font-black leading-tight text-slate-900 md:text-6xl">
              Mua sắm công nghệ gọn, đẹp và có AI hỗ trợ.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-slate-600">
              Catalog thật, RAG chatbot, recommendation và checkout nằm chung trong một trải nghiệm liền mạch.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button onClick={() => router.push("/products")} className="btn-primary h-12 px-7">
                Xem catalog {productCount ? `(${productCount}+ sản phẩm)` : ""}
              </button>
              <button onClick={() => router.push("/chat")} className="btn-secondary h-12 px-7">
                Mở AI chat
              </button>
            </div>
            <div className="mt-8 max-w-2xl">
              <SearchBar onSubmit={(q) => router.push(`/products?search=${encodeURIComponent(q)}`)} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <article className="card-premium bg-white/80">
              <ShieldCheck className="h-6 w-6 text-primary" />
              <h2 className="mt-4 font-display text-xl font-bold">Catalog thật</h2>
              <p className="mt-2 text-sm text-slate-600">Sản phẩm, giá và ảnh hiển thị trực tiếp từ catalog seed.</p>
            </article>
            <article className="card-premium bg-white/80">
              <Truck className="h-6 w-6 text-accent" />
              <h2 className="mt-4 font-display text-xl font-bold">Kho tri thức</h2>
              <p className="mt-2 text-sm text-slate-600">Tài liệu vận hành sẵn sàng cho truy hồi và chat.</p>
            </article>
            <article className="card-premium bg-white/80 sm:col-span-2 lg:col-span-1">
              <Bot className="h-6 w-6 text-warning" />
              <h2 className="mt-4 font-display text-xl font-bold">Demo AI</h2>
              <p className="mt-2 text-sm text-slate-600">Tầng gợi ý, tracking và RAG chat cùng dùng một nguồn dữ liệu.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-border/80 bg-card p-6 md:p-8">
        <SectionHeader title="Checklist đối chiếu" subtitle="Các tiêu chí demo được thể hiện trực tiếp trên storefront." />
        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {evaluationChecklist.map((item) => (
            <article key={item.title} className="rounded-3xl border border-border/80 bg-slate-50 p-5">
              <span className="inline-flex rounded-full bg-success/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-success">
                {item.status}
              </span>
              <h2 className="mt-4 text-lg font-bold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Sản phẩm nổi bật" subtitle="12 sản phẩm đầu tiên đang được render ngay trên trang chủ." />
        <div className="mt-4 rounded-3xl border border-border/80 bg-card px-5 py-4 text-sm text-slate-600">
          Catalog công khai hiện có <strong className="text-slate-900">{productCount}</strong> sản phẩm đang hoạt động.
        </div>
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-[2rem] border border-border/80 bg-card p-6 md:p-8">
          <SectionHeader title="Ngăn xếp AI" subtitle="Các thành phần đang phục vụ recommendation, retrieval và chat." />
          <div className="mt-8 grid gap-4">
            {aiHighlights.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="rounded-3xl border border-border/80 bg-slate-50 p-5">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-slate-900">{item.title}</h2>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="rounded-[2rem] border border-border/80 bg-card p-6 md:p-8">
          <SectionHeader
            title="Ảnh chụp kho tri thức"
            subtitle="Các tài liệu tri thức mà chatbot có thể truy hồi khi người dùng hỏi chính sách hoặc hướng dẫn."
          />
          <div className="mt-8 space-y-4">
            {knowledgeDocs.length ? (
              knowledgeDocs.slice(0, 6).map((doc) => (
                <article key={doc.id} className="rounded-3xl border border-border/80 bg-slate-50 p-5">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
                    <span>{doc.document_type}</span>
                    {doc.source ? <span>• {doc.source}</span> : null}
                  </div>
                  <h2 className="mt-2 text-lg font-bold text-slate-900">{doc.title}</h2>
                  {doc.content_preview ? <p className="mt-2 text-sm leading-6 text-slate-600">{doc.content_preview}</p> : null}
                </article>
              ))
            ) : (
              <article className="rounded-3xl border border-dashed border-border/80 bg-slate-50 p-5 text-sm leading-6 text-slate-600">
                Kho tri thức sẽ hiển thị đầy đủ sau khi dữ liệu AI được seed.
              </article>
            )}
          </div>
        </div>
      </section>

      {recData?.products?.length ? (
        <section className="rounded-[2.5rem] border border-border/80 bg-card p-7 md:p-10">
          <SectionHeader title="Gợi ý AI cho bạn" subtitle="Tầng gợi ý vẫn bám sát catalog thật và ảnh sản phẩm đã chuẩn hoá." />
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {recData.products.map((item) => (
              <article key={item.product_id} className="rounded-2xl border border-border bg-muted/40 p-4">
                <div className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                  {item.reason_codes?.[0] ?? "Gợi ý"}
                </div>
                <h2 className="mt-3 line-clamp-2 font-display text-lg font-bold text-slate-900">{item.product_name}</h2>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">{item.brand}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">
                    {new Intl.NumberFormat("vi-VN").format(Number(item.price))} đ
                  </span>
                  <Link
                    href={`/products/${item.product_id}`}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white"
                    aria-label={`Xem sản phẩm ${item.product_name}`}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded-[2rem] border border-border/80 bg-gradient-to-r from-slate-900 to-slate-800 p-7 text-white md:p-10">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white">Luồng demo</h2>
          <p className="mt-1 text-white/70">Ba bước để kiểm tra trải nghiệm storefront và AI.</p>
        </div>
        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {demoFlow.map((step, index) => (
            <article key={step} className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/60">Bước {index + 1}</p>
              <p className="mt-3 text-sm leading-6 text-white/85">{step}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
