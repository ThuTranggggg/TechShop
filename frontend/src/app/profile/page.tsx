"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { clearAuth } from "@/services/auth";
import { getAddresses, me } from "@/services/api/user";

export default function ProfilePage() {
  const router = useRouter();
  const { data: profile } = useQuery({ queryKey: ["me"], queryFn: me });
  const { data: addresses } = useQuery({ queryKey: ["addresses"], queryFn: getAddresses });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section className="card-premium">
        <h1 className="text-2xl font-black text-slate-900">Hồ sơ tài khoản</h1>
        <div className="mt-5 grid gap-3 text-sm text-slate-700">
          <p><span className="font-semibold">Họ tên:</span> {profile?.full_name || "-"}</p>
          <p><span className="font-semibold">Email:</span> {profile?.email || "-"}</p>
          <p><span className="font-semibold">Vai trò:</span> {(profile as { role?: string } | undefined)?.role || "customer"}</p>
        </div>
        <button
          onClick={() => {
            clearAuth();
            router.push("/login");
          }}
          className="mt-6 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-primary"
        >
          Đăng xuất
        </button>
      </section>

      <section className="card-premium">
        <h2 className="text-xl font-bold">Địa chỉ đã lưu</h2>
        {!addresses?.length ? <p className="mt-3 text-sm text-slate-500">Chưa có địa chỉ nào.</p> : null}
        <div className="mt-4 grid gap-3">
          {addresses?.map((a) => (
            <article key={a.id} className="rounded-xl border border-border bg-white p-3 text-sm">
              <p className="font-semibold text-slate-900">{a.receiver_name} - {a.phone_number}</p>
              <p className="text-slate-600">{a.line1}, {a.district}, {a.city}, {a.country}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
