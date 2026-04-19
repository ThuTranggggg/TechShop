export function AppFooter() {
  return (
    <footer className="mt-20 border-t border-border/70 bg-card/70 backdrop-blur-sm">
      <div className="container-app py-12 text-sm text-slate-600">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-display text-lg font-bold text-slate-900">TechShop Experience Platform</p>
            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">Microservices Commerce Frontend + AI RAG Demo</p>
          </div>
          <div className="flex items-center gap-5">
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">Realtime Inventory</span>
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">AI Assisted</span>
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">Secure Checkout</span>
          </div>
        </div>
        <p className="mt-8 text-xs text-slate-500">Designed for interactive demo, knowledge-base-backed chat, and production-ready service integration.</p>
      </div>
    </footer>
  );
}
