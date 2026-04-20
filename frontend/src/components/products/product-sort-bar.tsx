"use client";

export function ProductSortBar({ onSort }: { onSort: (value: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-600">Sắp xếp</span>
      <select onChange={(e) => onSort(e.target.value)} className="rounded-xl border border-border p-2 text-sm">
        <option value="-published_at">Mới nhất</option>
        <option value="base_price">Giá tăng dần</option>
        <option value="-base_price">Giá giảm dần</option>
      </select>
    </div>
  );
}
