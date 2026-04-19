"use client";

import { Search } from "lucide-react";
import { FormEvent, useState } from "react";

export function SearchBar({ defaultValue = "", onSubmit }: { defaultValue?: string; onSubmit: (query: string) => void }) {
  const [value, setValue] = useState(defaultValue);
  const handleSubmit = (e: FormEvent) => { e.preventDefault(); onSubmit(value); };
  return (
    <form className="flex w-full items-center gap-2 rounded-[1.25rem] border border-border/80 bg-white/90 p-2 shadow-soft backdrop-blur" onSubmit={handleSubmit}>
      <Search className="ml-2 h-4 w-4 text-primary" />
      <input
        className="w-full border-none bg-transparent p-2 text-sm text-slate-700 outline-none placeholder:text-slate-400"
        placeholder="Tìm laptop, điện thoại, thương hiệu..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button className="rounded-[0.9rem] bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:brightness-95">
        Tìm
      </button>
    </form>
  );
}
