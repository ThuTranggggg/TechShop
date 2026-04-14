"use client";

import { useForm } from "react-hook-form";

export type AddressInput = { receiver_name: string; receiver_phone: string; line1: string; district: string; city: string; country: string; };

export function AddressForm({ onSubmit, loading }: { onSubmit: (data: AddressInput) => void; loading?: boolean }) {
  const { register, handleSubmit } = useForm<AddressInput>({ defaultValues: { country: "Vietnam" } });
  return <form className="grid grid-cols-1 gap-3" onSubmit={handleSubmit(onSubmit)}><input className="rounded-xl border border-border p-3" placeholder="Người nhận" {...register("receiver_name", { required: true })} /><input className="rounded-xl border border-border p-3" placeholder="Số điện thoại" {...register("receiver_phone", { required: true })} /><input className="rounded-xl border border-border p-3" placeholder="Địa chỉ" {...register("line1", { required: true })} /><div className="grid grid-cols-2 gap-3"><input className="rounded-xl border border-border p-3" placeholder="Quận/Huyện" {...register("district", { required: true })} /><input className="rounded-xl border border-border p-3" placeholder="Thành phố" {...register("city", { required: true })} /></div><input className="rounded-xl border border-border p-3" placeholder="Quốc gia" {...register("country", { required: true })} /><button disabled={loading} className="rounded-xl bg-slate-900 p-3 font-semibold text-white">{loading ? "Đang xử lý..." : "Tạo đơn hàng"}</button></form>;
}
