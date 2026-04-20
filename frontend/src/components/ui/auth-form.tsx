"use client";

import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

const schema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(6, "Mật khẩu tối thiểu 6 ký tự"),
});

type Input = z.infer<typeof schema>;

export function AuthForm({
  onSubmit,
  loading,
  defaultValues,
}: {
  onSubmit: (data: Input) => void;
  loading?: boolean;
  defaultValues?: Partial<Input>;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Input>({ resolver: zodResolver(schema), defaultValues });
  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-border bg-slate-50/80 p-2">
        <button
          type="button"
          className="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-950 hover:text-white"
          onClick={() => {
            setValue("email", "john@example.com");
            setValue("password", "Demo@123456");
          }}
        >
          Demo khách hàng
        </button>
        <button
          type="button"
          className="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-950 hover:text-white"
          onClick={() => {
            setValue("email", "admin@techshop.com");
            setValue("password", "Demo@123456");
          }}
        >
          Demo admin
        </button>
        <button
          type="button"
          className="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-950 hover:text-white"
          onClick={() => {
            setValue("email", "staff@techshop.com");
            setValue("password", "Demo@123456");
          }}
        >
          Demo nhân sự
        </button>
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-700">Email</label>
        <input
          {...register("email")}
          placeholder="john.doe@techshop.local"
          className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
        />
        {errors.email ? <p className="mt-1 text-sm text-red-600">{errors.email.message}</p> : null}
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-700">Mật khẩu</label>
        <input
          type="password"
          {...register("password")}
          placeholder="CustomerPass123!"
          className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-base outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
        />
        {errors.password ? <p className="mt-1 text-sm text-red-600">{errors.password.message}</p> : null}
      </div>
      <button disabled={loading} className="w-full rounded-xl bg-slate-950 p-3.5 text-base font-semibold text-white transition hover:bg-primary disabled:cursor-not-allowed disabled:opacity-80">
        {loading ? "Đang đăng nhập..." : "Đăng nhập"}
      </button>
    </form>
  );
}
