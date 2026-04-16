"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ShieldCheck, Sparkles, UserCircle2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { register as registerUser } from "@/services/api/user";
import { setAuth } from "@/services/auth";

const schema = z.object({
  full_name: z.string().min(2, "Họ tên quá ngắn"),
  email: z.string().email("Email không hợp lệ"),
  phone_number: z.string().optional().or(z.literal("")),
  password: z.string().min(6, "Mật khẩu tối thiểu 6 ký tự"),
  confirm_password: z.string().min(6, "Mật khẩu xác nhận tối thiểu 6 ký tự"),
}).refine((value) => value.password === value.confirm_password, {
  message: "Mật khẩu xác nhận không khớp",
  path: ["confirm_password"],
});

type Input = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { register, handleSubmit, formState: { errors } } = useForm<Input>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: "",
      email: "",
      phone_number: "",
      password: "",
      confirm_password: "",
    },
  });

  return (
    <section className="mx-auto grid max-w-6xl overflow-hidden rounded-[2.5rem] border border-border/80 bg-card shadow-premium lg:grid-cols-[1fr_1.1fr]">
      <aside className="relative hidden p-10 lg:block">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-transparent to-accent/15" />
        <div className="relative space-y-8">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Create Account
          </span>
          <h1 className="font-display text-4xl font-extrabold leading-tight text-slate-900">
            Tạo tài khoản
            <br />
            để dùng đầy đủ TechShop.
          </h1>
          <p className="max-w-md text-slate-600">
            Đăng ký để đồng bộ giỏ hàng, theo dõi đơn hàng và lưu lịch sử chat AI trên cùng một tài khoản.
          </p>
          <div className="grid gap-3">
            <div className="rounded-2xl border border-border bg-card/70 p-4">
              <ShieldCheck className="h-5 w-5 text-success" />
              <p className="mt-2 text-sm font-semibold text-slate-900">Kết nối với backend thật</p>
            </div>
            <div className="rounded-2xl border border-border bg-card/70 p-4">
              <UserCircle2 className="h-5 w-5 text-accent" />
              <p className="mt-2 text-sm font-semibold text-slate-900">Luồng đăng ký có thể kiểm thử bằng Playwright</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="p-8 md:p-12">
        <div className="mb-8">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-slate-800">
            <UserCircle2 className="h-8 w-8" />
          </div>
          <h2 className="mt-4 font-display text-3xl font-extrabold text-slate-900">Đăng ký tài khoản</h2>
          <p className="mt-2 text-sm text-slate-600">Tạo tài khoản mới để trải nghiệm các luồng demo.</p>
        </div>

        {error ? <div className="mb-6 rounded-2xl border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div> : null}

        <form
          className="space-y-5"
          onSubmit={handleSubmit(async (values) => {
            setLoading(true);
            setError("");
            try {
              const res = await registerUser(values);
              setAuth(res.access, res.refresh);
              router.push("/");
            } catch (e) {
              setError(e instanceof Error ? e.message : "Đăng ký thất bại");
            } finally {
              setLoading(false);
            }
          })}
        >
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Họ tên</label>
            <input {...register("full_name")} className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            {errors.full_name ? <p className="mt-1 text-sm text-red-600">{errors.full_name.message}</p> : null}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Email</label>
            <input {...register("email")} type="email" className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            {errors.email ? <p className="mt-1 text-sm text-red-600">{errors.email.message}</p> : null}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Số điện thoại</label>
            <input {...register("phone_number")} className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Mật khẩu</label>
            <input {...register("password")} type="password" className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            {errors.password ? <p className="mt-1 text-sm text-red-600">{errors.password.message}</p> : null}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Xác nhận mật khẩu</label>
            <input {...register("confirm_password")} type="password" className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            {errors.confirm_password ? <p className="mt-1 text-sm text-red-600">{errors.confirm_password.message}</p> : null}
          </div>
          <button disabled={loading} className="w-full rounded-xl bg-slate-950 p-3.5 text-base font-semibold text-white transition hover:bg-primary disabled:cursor-not-allowed disabled:opacity-80">
            {loading ? "Đang đăng ký..." : "Đăng ký"}
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-slate-600">
          Đã có tài khoản?{" "}
          <Link href="/login" className="font-bold text-primary hover:underline">
            Đăng nhập
          </Link>
        </p>
      </div>
    </section>
  );
}
