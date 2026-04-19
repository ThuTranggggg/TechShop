"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { register as registerUser, login } from "@/services/api/user";
import { setAuth } from "@/services/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    password_confirm: "",
    phone_number: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  return (
    <section className="mx-auto max-w-3xl rounded-[2.5rem] border border-border/80 bg-card p-8 shadow-premium md:p-12">
      <h1 className="text-3xl font-extrabold text-slate-900">Tạo tài khoản customer</h1>
      <p className="mt-2 text-sm text-slate-600">Tài khoản đăng ký mới mặc định mang role `customer` để demo đầy đủ luồng mua hàng.</p>

      {error ? <div className="mt-6 rounded-2xl border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <form
        className="mt-8 grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setLoading(true);
          setError("");
          try {
            await registerUser(form);
            const auth = await login({ email: form.email, password: form.password });
            setAuth(auth.access, auth.refresh);
            router.push("/");
          } catch (err) {
            setError(err instanceof Error ? err.message : "Đăng ký thất bại");
          } finally {
            setLoading(false);
          }
        }}
      >
        <input className="rounded-xl border border-border p-3" placeholder="Họ và tên" value={form.full_name} onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))} />
        <input className="rounded-xl border border-border p-3" placeholder="Email" type="email" value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} />
        <input className="rounded-xl border border-border p-3" placeholder="Số điện thoại" value={form.phone_number} onChange={(e) => setForm((prev) => ({ ...prev, phone_number: e.target.value }))} />
        <input className="rounded-xl border border-border p-3" placeholder="Mật khẩu" type="password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} />
        <input className="rounded-xl border border-border p-3" placeholder="Nhập lại mật khẩu" type="password" value={form.password_confirm} onChange={(e) => setForm((prev) => ({ ...prev, password_confirm: e.target.value }))} />
        <button disabled={loading} className="rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-70">
          {loading ? "Đang tạo tài khoản..." : "Đăng ký"}
        </button>
      </form>

      <p className="mt-6 text-sm text-slate-600">
        Đã có tài khoản?{" "}
        <Link href="/login" className="font-semibold text-primary">
          Đăng nhập
        </Link>
      </p>
    </section>
  );
}
