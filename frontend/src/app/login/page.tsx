"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, ShieldCheck, Sparkles, UserCircle2 } from "lucide-react";
import { AuthForm } from "@/components/ui/auth-form";
import { login } from "@/services/api/user";
import { setAuth } from "@/services/auth";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  return (
    <section className="mx-auto grid max-w-6xl overflow-hidden rounded-[2.5rem] border border-border/80 bg-card shadow-premium lg:grid-cols-[1fr_1.1fr]">
      <aside className="relative hidden p-10 lg:block">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-transparent to-accent/15" />
        <div className="relative space-y-8">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Secure Access
          </span>
          <h1 className="font-display text-4xl font-extrabold leading-tight text-slate-900">
            Chào mừng trở lại
            <br />
            với TechShop.
          </h1>
          <p className="max-w-md text-slate-600">
            Đăng nhập để đồng bộ giỏ hàng, theo dõi đơn hàng và nhận gợi ý cá nhân hóa từ AI assistant.
          </p>
          <div className="grid gap-3">
            <div className="rounded-2xl border border-border bg-card/70 p-4">
              <ShieldCheck className="h-5 w-5 text-success" />
              <p className="mt-2 text-sm font-semibold text-slate-900">Bảo mật token & session</p>
            </div>
            <div className="rounded-2xl border border-border bg-card/70 p-4">
              <KeyRound className="h-5 w-5 text-accent" />
              <p className="mt-2 text-sm font-semibold text-slate-900">Đăng nhập nhanh bằng tài khoản demo</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="p-8 md:p-12">
        <div className="mb-8">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-slate-800">
            <UserCircle2 className="h-8 w-8" />
          </div>
          <h2 className="mt-4 font-display text-3xl font-extrabold text-slate-900">Đăng nhập tài khoản</h2>
          <p className="mt-2 text-sm text-slate-600">Sử dụng tài khoản khách hàng hoặc admin để trải nghiệm luồng demo.</p>
        </div>

        {error ? <div className="mb-6 rounded-2xl border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

        <AuthForm
          loading={loading}
          defaultValues={{ email: "john@example.com", password: "Demo@123456" }}
          onSubmit={async (values) => {
            setLoading(true);
            setError("");
            try {
              const res = await login(values);
              setAuth(res.access, res.refresh);
              router.push("/");
            } catch (e) {
              setError(e instanceof Error ? e.message : "Đăng nhập thất bại");
            } finally {
              setLoading(false);
            }
          }}
        />

        <p className="mt-8 text-center text-sm text-slate-600">
          Chưa có tài khoản?{" "}
          <Link href="/register" className="font-bold text-primary hover:underline">
            Đăng ký ngay
          </Link>
        </p>
      </div>
    </section>
  );
}
