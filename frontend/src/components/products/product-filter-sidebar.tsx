"use client";

export function ProductFilterSidebar({ categories, brands, onChange }: { categories: Array<{ id: string; name: string }>; brands: Array<{ id: string; name: string }>; onChange: (v: Record<string, string>) => void }) {
  return (
    <aside className="card-premium rounded-[1.6rem] border border-border/70 bg-white/95 p-5">
      <h3 className="mb-4 text-sm font-black uppercase tracking-widest text-slate-900">Bộ lọc</h3>
      <div className="space-y-4 text-sm">
        <select className="w-full rounded-xl border border-border bg-white px-3 py-2.5 text-slate-700" onChange={(e) => onChange({ category: e.target.value })}>
          <option value="">Danh mục</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className="w-full rounded-xl border border-border bg-white px-3 py-2.5 text-slate-700" onChange={(e) => onChange({ brand: e.target.value })}>
          <option value="">Thương hiệu</option>
          {brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </div>
    </aside>
  );
}
