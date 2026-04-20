"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { MessageCircle, X, ArrowUpRight } from "lucide-react";
import { useUiStore } from "@/store/ui-store";
import { config } from "@/lib/config";
import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";
import { askAi, trackAiEvent, type AiRelatedProduct, type AiSource } from "@/services/api/ai";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";
import { useMounted } from "@/hooks/use-mounted";
import { getProductImageUrl } from "@/lib/product-image";

export function ChatWidget() {
  const { chatOpen, setChatOpen } = useUiStore();
  const mounted = useMounted();
  const token = getAccessToken();
  const userId = mounted && token ? extractUserIdFromJwt(token) : undefined;
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string; sources?: AiSource[]; relatedProducts?: AiRelatedProduct[] }>>([]);
  const [relatedProducts, setRelatedProducts] = useState<AiRelatedProduct[]>([]);
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    const q = value;
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setValue("");
    setLoading(true);
    try {
      const res = await askAi({ query: q, user_id: userId });
      trackAiEvent({ event_type: "chat_query", user_id: userId, keyword: q, metadata: { source: "chat_widget" } }).catch(() => undefined);
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: res.answer,
        sources: res.sources,
        relatedProducts: res.related_products,
      }]);
      setRelatedProducts((prev) => [...prev, ...(res.related_products ?? [])]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Hiện tại mình chưa lấy được dữ liệu từ dịch vụ AI." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {chatOpen ? (
        <div className="w-[min(92vw,34rem)] rounded-3xl border border-border bg-slate-50 p-4 shadow-2xl">
          <div className="mb-3 flex items-center justify-between">
            <p className="font-semibold">Trợ lý AI</p>
            <button onClick={() => setChatOpen(false)} className="rounded-full p-1 hover:bg-slate-200">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mb-3 flex max-h-[32rem] min-h-[26rem] flex-col gap-2 overflow-y-auto rounded-2xl bg-white p-3">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "ml-auto" : ""}>
                <ChatMessageBubble role={m.role} text={m.text} />
                {m.sources?.length ? (
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
                    {m.sources.map((source, index) => (
                      <Link
                        key={`${source.document_title}-${index}`}
                        href={`/products?search=${encodeURIComponent(source.document_title || source.document_type || "")}`}
                        className="rounded-full border border-border bg-white px-2 py-1 transition-colors hover:bg-slate-100"
                      >
                        {source.document_title || source.document_type || "Nguồn"}
                      </Link>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
            {loading ? <ChatMessageBubble role="assistant" text="Đang suy nghĩ..." /> : null}
            {relatedProducts.length ? (
              <div className="mt-2 grid grid-cols-1 gap-2">
                {relatedProducts.slice(0, 4).map((product, index) => (
                  <Link
                    key={`${product.id ?? index}`}
                    href={product.id ? `/products/${product.id}` : "/products"}
                    className="flex items-center gap-3 rounded-2xl border border-border bg-slate-50 p-3 transition-colors hover:bg-slate-100"
                  >
                    <img
                      src={getProductImageUrl(product)}
                      alt={product.name || "Sản phẩm liên quan"}
                      className="h-12 w-12 rounded-xl object-cover"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-slate-900">{product.name || "Sản phẩm liên quan"}</div>
                      {typeof product.base_price === "number" ? (
                        <div className="text-xs text-slate-500">{new Intl.NumberFormat("vi-VN").format(product.base_price)} đ</div>
                      ) : null}
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-slate-400" />
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
          <div className="mb-3 flex flex-wrap gap-2">
            {config.aiSuggestions.slice(0, 2).map((s) => (
              <button key={s} onClick={() => setValue(s)} className="rounded-full bg-slate-200 px-3 py-1.5 text-xs">
                {s}
              </button>
            ))}
          </div>
          {mounted && token ? (
            <form onSubmit={submit} className="flex gap-2">
              <input className="w-full rounded-xl border border-border p-3 text-sm" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Nhập câu hỏi..." />
              <button className="rounded-xl bg-slate-900 px-4 text-sm text-white">Gửi câu hỏi</button>
            </form>
          ) : (
            <p className="rounded-xl border border-dashed border-border bg-white p-3 text-xs text-slate-500">Đăng nhập để dùng AI chat và lưu lịch sử hội thoại.</p>
          )}
        </div>
      ) : (
        <button onClick={() => setChatOpen(true)} className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-2xl">
          <MessageCircle className="h-4 w-4" /> Hỏi AI
        </button>
      )}
    </div>
  );
}
