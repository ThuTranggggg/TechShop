export function AppFooter() {
  return (
    <footer className="mt-20 border-t border-border/70 bg-card/70 backdrop-blur-sm">
      <div className="container-app py-12 text-sm text-slate-600">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-lg font-bold text-slate-900">Nền tảng trải nghiệm TechShop</p>
            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">Nền tảng storefront microservices + demo AI RAG</p>
          </div>
          <div className="flex items-center gap-5">
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">Tồn kho real-time</span>
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">AI hỗ trợ</span>
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">Thanh toán an toàn</span>
          </div>
        </div>
        <p className="mt-8 text-xs text-slate-500">
          Thiết kế cho demo tương tác, chat có tri thức nền và luồng tích hợp dịch vụ rõ ràng.
        </p>
      </div>
    </footer>
  );
}
