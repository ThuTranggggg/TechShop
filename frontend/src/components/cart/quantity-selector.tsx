"use client";

import { Minus, Plus } from "lucide-react";

export function QuantitySelector({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="inline-flex items-center rounded-xl border border-border bg-white">
      <button className="p-2" onClick={() => onChange(Math.max(1, value - 1))} aria-label="Giảm số lượng"><Minus className="h-4 w-4" /></button>
      <span className="w-10 text-center text-sm font-semibold">{value}</span>
      <button className="p-2" onClick={() => onChange(value + 1)} aria-label="Tăng số lượng"><Plus className="h-4 w-4" /></button>
    </div>
  );
}
