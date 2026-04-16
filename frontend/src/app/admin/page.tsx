"use client";

import { FormEvent, useMemo, useState } from "react";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt, extractUserRoleFromJwt } from "@/lib/jwt";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminCreateProduct, adminDeleteProduct, adminListProducts, adminUpdateProduct } from "@/services/api/admin";
import { getBrands, getCategories, getProductTypes } from "@/services/api/products";
import { EmptyState } from "@/components/ui/empty-state";
import { getOrders } from "@/services/api/orders";
import { getUserPreferenceSummary } from "@/services/api/ai";
import { formatPrice } from "@/lib/utils";
import { useMounted } from "@/hooks/use-mounted";

type ProductForm = {
  id?: string;
  name: string;
  slug: string;
  short_description: string;
  description: string;
  category: string;
  brand: string;
  product_type: string;
  base_price: number;
  currency: string;
  thumbnail_url: string;
};

const INITIAL_FORM: ProductForm = {
  name: "",
  slug: "",
  short_description: "",
  description: "",
  category: "",
  brand: "",
  product_type: "",
  base_price: 1000000,
  currency: "VND",
  thumbnail_url: "",
};

export default function AdminPage() {
  const mounted = useMounted();
  const token = getAccessToken();
  const userId = mounted && token ? extractUserIdFromJwt(token) : "";
  const role = mounted && token ? extractUserRoleFromJwt(token) : "";
  const isAdmin = role === "admin" || role === "staff";
  const qc = useQueryClient();
  const [form, setForm] = useState<ProductForm>(INITIAL_FORM);
  const [editingId, setEditingId] = useState<string>("");

  const { data: products } = useQuery({ queryKey: ["admin-products"], queryFn: adminListProducts });
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: getCategories });
  const { data: brands } = useQuery({ queryKey: ["brands"], queryFn: getBrands });
  const { data: productTypes } = useQuery({ queryKey: ["product-types"], queryFn: getProductTypes });
  const { data: orders } = useQuery({ queryKey: ["admin-orders"], queryFn: getOrders, enabled: mounted && isAdmin });
  const { data: aiPreference } = useQuery({
    queryKey: ["admin-ai-preference", userId],
    queryFn: () => getUserPreferenceSummary(userId),
    // Admin CRUD should stay usable even if the customer preference endpoint is flaky.
    enabled: false,
  });

  const createMutation = useMutation({
    mutationFn: adminCreateProduct,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-products"] });
      setForm(INITIAL_FORM);
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => adminUpdateProduct(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-products"] });
      setEditingId("");
      setForm(INITIAL_FORM);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: adminDeleteProduct,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-products"] }),
  });

  const canSubmit = useMemo(
    () => Boolean(form.name && form.slug && form.category && form.brand && form.product_type && Number(form.base_price) > 0),
    [form],
  );

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const payload = {
      name: form.name,
      slug: form.slug,
      short_description: form.short_description,
      description: form.description,
      category: form.category,
      brand: form.brand,
      product_type: form.product_type,
      base_price: Number(form.base_price),
      currency: form.currency,
      thumbnail_url: form.thumbnail_url,
      is_active: true,
      is_featured: false,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  if (!mounted || !isAdmin) {
    return <div className="card-premium mx-auto max-w-4xl"><h1 className="text-xl font-bold">Bạn không có quyền truy cập khu vực Admin.</h1></div>;
  }

  const totalRevenue = (orders ?? []).reduce((acc, o) => acc + Number(o.totals?.grand_total ?? 0), 0);
  const processingOrders = (orders ?? []).filter((o) => !["delivered", "cancelled"].includes(String(o.status).toLowerCase())).length;

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <section className="card-premium">
        <h1 className="text-2xl font-black text-slate-900">Admin Dashboard</h1>
        <p className="mt-2 text-sm text-slate-600">Quản trị vận hành storefront: catalog, đơn hàng và tín hiệu AI.</p>
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <article className="rounded-2xl border border-border bg-white p-3">
            <p className="text-xs uppercase tracking-widest text-slate-500">Tổng sản phẩm</p>
            <p className="mt-1 text-xl font-black text-slate-900">{products?.count ?? products?.results?.length ?? 0}</p>
          </article>
          <article className="rounded-2xl border border-border bg-white p-3">
            <p className="text-xs uppercase tracking-widest text-slate-500">Danh mục</p>
            <p className="mt-1 text-xl font-black text-slate-900">{categories?.results?.length ?? 0}</p>
          </article>
          <article className="rounded-2xl border border-border bg-white p-3">
            <p className="text-xs uppercase tracking-widest text-slate-500">Đơn đang xử lý</p>
            <p className="mt-1 text-xl font-black text-slate-900">{processingOrders}</p>
          </article>
          <article className="rounded-2xl border border-border bg-white p-3">
            <p className="text-xs uppercase tracking-widest text-slate-500">Doanh thu demo</p>
            <p className="mt-1 text-xl font-black text-slate-900">{formatPrice(totalRevenue, "VND")}</p>
          </article>
        </div>
      </section>

      <section className="card-premium">
        <h2 className="text-xl font-bold">{editingId ? "Cập nhật sản phẩm" : "Tạo sản phẩm mới"}</h2>
        <form onSubmit={submit} className="mt-4 grid gap-3 md:grid-cols-2">
          <input className="rounded-xl border border-border p-3" placeholder="Tên sản phẩm" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
          <input className="rounded-xl border border-border p-3" placeholder="Slug" value={form.slug} onChange={(e) => setForm((p) => ({ ...p, slug: e.target.value }))} />
          <select className="rounded-xl border border-border p-3" value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}>
            <option value="">Chọn danh mục</option>
            {categories?.results?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select className="rounded-xl border border-border p-3" value={form.brand} onChange={(e) => setForm((p) => ({ ...p, brand: e.target.value }))}>
            <option value="">Chọn thương hiệu</option>
            {brands?.results?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <select className="rounded-xl border border-border p-3" value={form.product_type} onChange={(e) => setForm((p) => ({ ...p, product_type: e.target.value }))}>
            <option value="">Chọn loại sản phẩm</option>
            {productTypes?.results?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <input className="rounded-xl border border-border p-3" placeholder="Giá" type="number" value={form.base_price} onChange={(e) => setForm((p) => ({ ...p, base_price: Number(e.target.value) }))} />
          <input className="rounded-xl border border-border p-3" placeholder="Ảnh thumbnail URL" value={form.thumbnail_url} onChange={(e) => setForm((p) => ({ ...p, thumbnail_url: e.target.value }))} />
          <input className="rounded-xl border border-border p-3 md:col-span-2" placeholder="Mô tả ngắn" value={form.short_description} onChange={(e) => setForm((p) => ({ ...p, short_description: e.target.value }))} />
          <textarea className="min-h-28 rounded-xl border border-border p-3 md:col-span-2" placeholder="Mô tả chi tiết" value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} />
          <div className="md:col-span-2 flex gap-2">
            <button disabled={!canSubmit} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-70">
              {editingId ? "Cập nhật" : "Tạo mới"}
            </button>
            {editingId ? (
              <button type="button" onClick={() => { setEditingId(""); setForm(INITIAL_FORM); }} className="rounded-xl border border-border px-4 py-2 text-sm font-semibold">
                Huỷ chỉnh sửa
              </button>
            ) : null}
          </div>
        </form>
      </section>

      <section className="card-premium">
        <h2 className="text-xl font-bold">Danh sách sản phẩm</h2>
        {!products?.results?.length ? <EmptyState title="Chưa có sản phẩm" description="Tạo sản phẩm mới để quản trị catalog." /> : null}
        <div className="mt-4 grid gap-3">
          {products?.results?.map((p) => (
            <article key={p.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-white p-3">
              <div>
                <h3 className="font-semibold text-slate-900">{p.name}</h3>
                <p className="text-xs text-slate-500">{p.slug} • {new Intl.NumberFormat("vi-VN").format(Number(p.base_price))} đ</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setEditingId(p.id);
                    setForm({
                      id: p.id,
                      name: p.name,
                      slug: p.slug,
                      short_description: p.short_description || "",
                      description: p.description || "",
                      category: String((p as { category?: string }).category || ""),
                      brand: String((p as { brand?: string }).brand || ""),
                      product_type: String((p as { product_type?: string }).product_type || ""),
                      base_price: Number(p.base_price),
                      currency: p.currency || "VND",
                      thumbnail_url: p.thumbnail_url || "",
                    });
                  }}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold"
                >
                  Sửa
                </button>
                <button onClick={() => deleteMutation.mutate(p.id)} className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white">
                  Xoá
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="card-premium">
        <h2 className="text-xl font-bold">Quản lý đơn hàng</h2>
        {!orders?.length ? <EmptyState title="Chưa có đơn hàng" description="Đơn hàng mới sẽ xuất hiện tại đây để theo dõi vận hành." /> : null}
        <div className="mt-4 grid gap-3">
          {orders?.slice(0, 8).map((o) => (
            <article key={o.id} className="rounded-xl border border-border bg-white p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-slate-900">{o.order_number}</h3>
                  <p className="text-xs text-slate-500">Thanh toán: {o.payment_status} • Fulfillment: {o.fulfillment_status || "-"}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{String(o.status).toUpperCase()}</span>
              </div>
              <p className="mt-2 text-sm font-semibold text-slate-900">{formatPrice(Number(o.totals?.grand_total ?? 0), o.totals?.currency || "VND")}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card-premium">
        <h2 className="text-xl font-bold">AI Monitoring</h2>
        {!aiPreference ? (
          <p className="mt-3 text-sm text-slate-500">Chưa có đủ tín hiệu hành vi để hiển thị hồ sơ AI cá nhân.</p>
        ) : (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <article className="rounded-xl border border-border bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Top brands</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {aiPreference.top_brands?.slice(0, 5).map((b) => (
                  <span key={b.brand_name} className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                    {b.brand_name} ({Math.round(Number(b.score ?? 0))})
                  </span>
                ))}
              </div>
            </article>
            <article className="rounded-xl border border-border bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500">Top categories</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {aiPreference.top_categories?.slice(0, 5).map((c) => (
                  <span key={c.category_name} className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
                    {c.category_name} ({Math.round(Number(c.score ?? 0))})
                  </span>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-600">Purchase intent score: {Math.round(Number(aiPreference.purchase_intent_score ?? 0))}</p>
            </article>
          </div>
        )}
      </section>
    </div>
  );
}
