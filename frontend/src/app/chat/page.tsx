"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { config } from "@/lib/config";
import { askAi, createChatSession, trackAiEvent } from "@/services/api/ai";
import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";
import { getOrders } from "@/services/api/orders";

export default function ChatPage() {
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<
    Array<{
      role: "user" | "assistant";
      text: string;
      sources?: Array<{ document_title?: string; document_type?: string }>;
      relatedProducts?: Array<{ product_id?: string; name?: string; price?: number }>;
    }>
  >([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const { data: orders } = useQuery({
    queryKey: ["chat-orders", userId],
    queryFn: getOrders,
    enabled: Boolean(userId),
  });
  const latestOrder = useMemo(
    () => (orders ?? []).slice().sort((a, b) => (String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""))))[0],
    [orders]
  );

  const buildContext = (text: string) => {
    const lowered = text.toLowerCase();
    if (!latestOrder) return undefined;
    if (lowered.includes("đơn") || lowered.includes("order") || lowered.includes("trạng thái") || lowered.includes("tình trạng")) {
      return {
        order_id: latestOrder.id,
        order_number: latestOrder.order_number,
        status: latestOrder.status,
        payment_status: latestOrder.payment_status,
        fulfillment_status: latestOrder.fulfillment_status,
        total: latestOrder.totals?.grand_total,
        currency: latestOrder.totals?.currency,
      };
    }
    return undefined;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const text = query;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setQuery("");
    setLoading(true);

    try {
      let sid = sessionId;
      if (!sid) {
        const s = await createChatSession(userId);
        sid = s.id;
        setSessionId(sid);
      }
      const answer = await askAi({ session_id: sid, query: text, user_id: userId, context: buildContext(text) });
      trackAiEvent({ event_type: "chat_query", user_id: userId, keyword: text, metadata: { session_id: sid } }).catch(() => undefined);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: answer.answer,
          sources: answer.sources,
          relatedProducts: answer.related_products?.map((item) => ({
            product_id: item.product_id,
            name: item.name,
            price: item.price,
          })),
        },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "AI service tam thoi khong kha dung." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl rounded-3xl border border-border bg-white p-6 lg:p-8">
      <h1 className="text-2xl font-bold">AI Assistant</h1>
      <p className="text-sm text-slate-600">Hoi ve san pham, don hang, chinh sach.</p>
      <div className="mt-3 flex flex-wrap gap-2">{config.aiSuggestions.map((s) => <button key={s} onClick={() => setQuery(s)} className="rounded-full bg-slate-100 px-3 py-1 text-xs">{s}</button>)}</div>
      <div className="mt-4 flex min-h-[560px] flex-col gap-3 rounded-2xl bg-slate-50 p-4">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "ml-auto max-w-[85%]" : "max-w-[85%]"}>
            <ChatMessageBubble role={m.role} text={m.text} />
            {m.sources?.length ? (
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                {m.sources.map((source, index) => (
                  <Link
                    key={`${source.document_title}-${index}`}
                    href={`/products?search=${encodeURIComponent(source.document_title || source.document_type || "")}`}
                    className="rounded-full bg-slate-100 px-2 py-1 transition-colors hover:bg-slate-200"
                  >
                    {source.document_title || source.document_type || "Nguon"}
                  </Link>
                ))}
              </div>
            ) : null}
            {m.relatedProducts?.length ? (
              <div className="mt-2 grid grid-cols-1 gap-2 text-xs text-slate-600">
                {m.relatedProducts.map((product, index) => (
                  <Link key={`${product.product_id}-${index}`} href={product.product_id ? `/products/${product.product_id}` : "/products"} className="flex items-center gap-2 rounded-2xl border border-border bg-white px-3 py-2 transition-colors hover:bg-slate-50">
                    <span className="min-w-0 flex-1 truncate">
                      {product.name}
                      {product.price ? ` - ${new Intl.NumberFormat("vi-VN").format(product.price)} đ` : ""}
                    </span>
                    <ArrowUpRight className="h-3.5 w-3.5 text-slate-400" />
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        ))}
        {loading ? <ChatMessageBubble role="assistant" text="Dang phan tich..." /> : null}
      </div>
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2"><input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full rounded-xl border border-border p-3" placeholder="Nhap cau hoi..." /><button className="rounded-xl bg-slate-900 px-5 text-sm font-semibold text-white">Gui</button></form>
    </div>
  );
}
