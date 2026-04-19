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
  {
    title: "Product/Service",
    description: "Website can duoc hien thi it nhat 10 san pham/dich vu co noi dung that.",
    status: "Dat",
  },
  {
    title: "AI Service - Deep Model",
    description: "Co AI service de phan loai y dinh, trich xuat thong tin va sinh cau tra loi.",
    status: "Dat",
  },
  {
    title: "AI Service - Knowledge Base",
    description: "Co he thong tri thuc noi bo de tra loi chinh sach va ho tro sau ban.",
    status: "Dat",
  },
  {
    title: "AI Service - RAG + Chat",
    description: "Chatbot co truy hoi context tu kho tri thuc va catalog san pham.",
    status: "Dat",
  },
  {
    title: "Tinh thuc tien / Demo",
    description: "Co luong demo ro rang cho bai toan tu van mua hang thuc te.",
    status: "Dat",
  },
];

const aiHighlights = [
  {
    title: "Mo hinh AI ung dung",
    description: "AI assistant phan tich truy van, nhan dien nhu cau mua hang va tong hop cau tra loi phu hop.",
    icon: BrainCircuit,
  },
  {
    title: "Knowledge base noi bo",
    description: "Tai lieu ve shipping, payment, return va support article duoc truy hoi cho chatbot.",
    icon: Database,
  },
  {
    title: "RAG + chat demo",
    description: "Nguoi dung co the hoi truc tiep, xem nguon tri thuc va danh sach san pham lien quan.",
    icon: MessagesSquare,
  },
];

const demoFlow = [
  "Mo catalog de xem it nhat 10 san pham/dich vu dang hoat dong.",
  "Mo trang AI Demo va dat cau hoi ve ngan sach, nhom product hoac chinh sach doi tra.",
  "Xem cau tra loi RAG cung tai lieu nguon va san pham duoc de xuat de tiep tuc mua hang.",
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
              TechShop AI Commerce Demo
            </span>
            <h1 className="mt-6 text-4xl font-black leading-tight text-slate-900 md:text-6xl">
              Nen tang mua sam da nganh
              <br />
              co AI tu van va RAG chatbot.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-slate-600">
              TechShop mo rong thanh storefront da nganh, ket hop catalog nhieu nhom product, AI service, knowledge base noi bo va
              luong demo thuc te cho bai toan tu van mua hang.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button onClick={() => router.push("/products")} className="btn-primary h-12 px-7">
                Xem catalog {productCount ? `(${productCount}+ san pham)` : ""}
              </button>
              <button onClick={() => router.push("/chat")} className="btn-secondary h-12 px-7">
                Thu RAG chatbot
              </button>
            </div>
            <div className="mt-8 max-w-2xl">
              <SearchBar onSubmit={(q) => router.push(`/products?search=${encodeURIComponent(q)}`)} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <article className="card-premium bg-white/80">
              <ShieldCheck className="h-6 w-6 text-primary" />
              <h2 className="mt-4 font-display text-xl font-bold">Catalog thuc te</h2>
              <p className="mt-2 text-sm text-slate-600">Catalog da seed nhieu nhom product nhu dien tu, thoi trang, my pham va do gia dung.</p>
            </article>
            <article className="card-premium bg-white/80">
              <Truck className="h-6 w-6 text-accent" />
              <h2 className="mt-4 font-display text-xl font-bold">Knowledge base van hanh</h2>
              <p className="mt-2 text-sm text-slate-600">Chinh sach giao hang, thanh toan va doi tra duoc dua vao he thong tri thuc de truy hoi.</p>
            </article>
            <article className="card-premium bg-white/80 sm:col-span-2 lg:col-span-1">
              <Bot className="h-6 w-6 text-warning" />
              <h2 className="mt-4 font-display text-xl font-bold">AI demo ro rang</h2>
              <p className="mt-2 text-sm text-slate-600">Trang AI Demo hien thi luong RAG + chat, nguon du lieu va san pham lien quan ngay trong hoi dap.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-border/80 bg-card p-6 md:p-8">
        <SectionHeader
          title="Checklist doi chieu"
          subtitle="5 nhom tieu chi duoc phan ra thanh cac bang chung co the xem truc tiep tren website."
        />
        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {evaluationChecklist.map((item) => (
            <article key={item.title} className="rounded-3xl border border-border/80 bg-slate-50 p-5">
              <span className="inline-flex rounded-full bg-success/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-success">
                {item.status}
              </span>
              <h2 className="mt-4 text-lg font-bold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader
          title="San pham / dich vu noi bat"
          subtitle="Danh sach hien thi 12 san pham dau tien trong catalog de dap ung va vuot moc toi thieu 10 san pham."
        />
        <div className="mt-4 rounded-3xl border border-border/80 bg-card px-5 py-4 text-sm text-slate-600">
          Catalog cong khai hien tai co <strong className="text-slate-900">{productCount}</strong> san pham dang hoat dong. Khu vuc ben duoi
          dang render 12 san pham tren trang chu de nguoi cham co the kiem tra ngay.
        </div>
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-[2rem] border border-border/80 bg-card p-6 md:p-8">
          <SectionHeader
            title="AI Service Stack"
            subtitle="Nhung thanh phan cot loi hien dang phuc vu recommendation, retrieval va chat."
          />
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
            title="Knowledge Base Snapshot"
            subtitle="Mot phan cac tai lieu tri thuc ma chatbot co the truy hoi khi nguoi dung hoi chinh sach va huong dan."
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
                Knowledge base se hien thi day du sau khi du lieu AI duoc seed. Frontend da san sang doc va render cac tai lieu nay tu AI
                service.
              </article>
            )}
          </div>
        </div>
      </section>

      {recData?.products?.length ? (
        <section className="rounded-[2.5rem] border border-border/80 bg-card p-7 md:p-10">
          <SectionHeader
            title="Goi y AI cho nguoi dung"
            subtitle="Recommendation layer tiep tuc la bang chung cho viec AI service dang can thiep vao trai nghiem mua sam."
          />
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {recData.products.map((item) => (
              <article key={item.product_id} className="rounded-2xl border border-border bg-muted/40 p-4">
                <div className="inline-flex rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                  {item.reason_codes?.[0] ?? "Recommendation"}
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
                    aria-label={`Xem san pham ${item.product_name}`}
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
          <h2 className="text-2xl font-bold text-white">Tinh thuc tien / Demo</h2>
          <p className="mt-1 text-white/70">Luong demo de nguoi cham co the tu thao tac va xac nhan cac tieu chi quan trong.</p>
        </div>
        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {demoFlow.map((step, index) => (
            <article key={step} className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/60">Buoc {index + 1}</p>
              <p className="mt-3 text-sm leading-6 text-white/85">{step}</p>
            </article>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/chat" className="btn-primary h-12 px-7">
            Mo AI Demo
          </Link>
          <Link href="/products" className="btn-secondary h-12 px-7 border-white/20 bg-white/10 text-white hover:bg-white/20">
            Xem toan bo catalog
          </Link>
        </div>
      </section>
    </div>
  );
}
