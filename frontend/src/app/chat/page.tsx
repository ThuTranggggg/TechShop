"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Database, MessageSquareText, Sparkles } from "lucide-react";
import { config } from "@/lib/config";
import { extractUserIdFromJwt } from "@/lib/jwt";
import { getAccessToken } from "@/services/auth";
import { askAi, createChatSession, getKnowledgeDocuments, type AiRelatedProduct, type AiSource } from "@/services/api/ai";
import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  sources?: AiSource[];
  relatedProducts?: AiRelatedProduct[];
};

const demoPrompts = [
  "Tư vấn một routine chăm sóc da dưới 500 nghìn.",
  "Chính sách đổi trả của TechShop như thế nào?",
  "Gợi ý một bộ đồ cắm trại cho cuối tuần.",
];

const ragSteps = [
  "Người dùng đặt câu hỏi về sản phẩm, đơn hàng hoặc chính sách.",
  "AI phân loại intent, trích xuất nhóm sản phẩm, danh mục và mức giá rồi tìm tài liệu liên quan.",
  "Hệ thống hợp nhất ngữ cảnh từ catalog + kho tri thức rồi sinh câu trả lời trong chat.",
];

export default function ChatPage() {
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: knowledgeData } = useQuery({
    queryKey: ["ai-knowledge-documents"],
    queryFn: getKnowledgeDocuments,
  });

  const knowledgeDocs = knowledgeData?.documents ?? [];
  const knowledgeCount = knowledgeData?.count ?? knowledgeDocs.length;

  const capabilityCards = useMemo(
    () => [
      {
        title: "Mô hình sâu",
        description: "Dịch vụ AI phân loại ý định, trích xuất thực thể và sinh câu trả lời từ ngữ cảnh đã truy hồi.",
        icon: Bot,
      },
      {
        title: "Kho tri thức",
        description: `${knowledgeCount} tài liệu tri thức đang sẵn sàng cho giao hàng, thanh toán, đổi trả và hướng dẫn.`,
        icon: Database,
      },
      {
        title: "RAG + Chat",
        description: "Mỗi câu trả lời có thể hiển thị tài liệu nguồn và gợi ý sản phẩm liên quan ngay trong khung chat.",
        icon: MessageSquareText,
      },
    ],
    [knowledgeCount],
  );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const text = query.trim();
    setMessages((prev) => [...prev, { role: "user", text }]);
    setQuery("");
    setLoading(true);

    try {
      let sid = sessionId;
      if (!sid) {
        const session = await createChatSession(userId);
        sid = session.id;
        setSessionId(sid);
      }

      const answer = await askAi({
        session_id: sid,
        query: text,
        user_id: userId,
        context: { source: "chat_page_demo" },
      });

      if (answer.session_id) setSessionId(answer.session_id);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: answer.answer,
          sources: answer.sources,
          relatedProducts: answer.related_products,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Dịch vụ AI tạm thời chưa phản hồi. Bạn có thể thử lại với một câu hỏi ngắn hơn.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-border/80 bg-gradient-to-br from-orange-50 via-white to-emerald-50 p-6 shadow-soft lg:p-8">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Demo dịch vụ AI
            </span>
            <h1 className="mt-4 text-3xl font-black text-slate-900 md:text-5xl">RAG chatbot cho bài toán tư vấn mua hàng thực tế.</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              Trang này cho thấy ba thành phần chính: mô hình AI, kho tri thức và quy trình RAG + chat. Bạn có thể đặt câu hỏi,
              xem tài liệu nguồn đã truy hồi và mở nhanh sản phẩm liên quan ngay trong phản hồi.
            </p>
          </div>
          <div className="grid gap-3">
            {capabilityCards.map((card) => {
              const Icon = card.icon;
              return (
                <article key={card.title} className="rounded-3xl border border-white/70 bg-white/80 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h2 className="font-display text-lg font-bold text-slate-900">{card.title}</h2>
                      <p className="text-sm text-slate-600">{card.description}</p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-border bg-white p-5 shadow-soft lg:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Trợ lý mua sắm AI</h2>
              <p className="mt-1 text-sm text-slate-600">Hỏi về sản phẩm, đơn hàng, thanh toán, đổi trả và chính sách giao hàng.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary">Dựa trên mô hình</span>
              <span className="rounded-full bg-accent/10 px-3 py-1 text-accent">{knowledgeCount} tài liệu</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">RAG + truy hồi catalog</span>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {[...config.aiSuggestions, ...demoPrompts].map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => setQuery(suggestion)}
                className="rounded-full border border-border bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-100"
              >
                {suggestion}
              </button>
            ))}
          </div>

          <div className="mt-4 flex min-h-[560px] flex-col gap-3 rounded-[2rem] bg-slate-50 p-4">
            {messages.length ? (
              messages.map((message, index) => (
                <ChatMessageBubble
                  key={`${message.role}-${index}`}
                  role={message.role}
                  text={message.text}
                  sources={message.sources}
                  relatedProducts={message.relatedProducts}
                />
              ))
            ) : (
              <div className="flex min-h-[500px] flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-border bg-white px-6 text-center">
                <Bot className="h-10 w-10 text-primary" />
                <h3 className="mt-4 text-xl font-bold text-slate-900">Sẵn sàng demo RAG + Chat</h3>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">
                  Hãy hỏi về mỹ phẩm, mẹ và bé, đồ gia dụng, chính sách đổi trả, thanh toán hoặc vận chuyển. Phản hồi sẽ hiển thị tài
                  liệu tri thức đã truy hồi khi có.
                </p>
              </div>
            )}
            {loading ? <ChatMessageBubble role="assistant" text="Đang truy hồi tri thức và tổng hợp câu trả lời..." /> : null}
          </div>

          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full"
              placeholder="Nhập câu hỏi để bắt đầu demo AI..."
              aria-label="Nhập câu hỏi cho AI"
            />
            <button type="submit" className="btn-primary h-12 px-6" disabled={loading}>
              Gửi câu hỏi
            </button>
          </form>
        </div>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <h2 className="text-xl font-bold text-slate-900">Quy trình RAG</h2>
            <div className="mt-4 space-y-3">
              {ragSteps.map((step, index) => (
                <article key={step} className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Bước {index + 1}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{step}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Kho tri thức</h2>
                <p className="mt-1 text-sm text-slate-600">Nguồn tri thức nội bộ mà chatbot đang dùng để truy hồi.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{knowledgeCount} tài liệu</span>
            </div>

            <div className="mt-4 space-y-3">
              {knowledgeDocs.length ? (
                knowledgeDocs.map((doc) => (
                  <article key={doc.id} className="rounded-2xl border border-border/80 bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">{doc.title}</h3>
                        <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                          {doc.document_type} {doc.source ? `• ${doc.source}` : ""}
                        </p>
                      </div>
                    </div>
                    {doc.content_preview ? <p className="mt-2 text-sm leading-6 text-slate-600">{doc.content_preview}</p> : null}
                  </article>
                ))
              ) : (
                <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                  Chưa tải được danh sách tri thức. Nếu backend chưa seed dữ liệu, hãy chạy seeding để hiển thị đầy đủ.
                </p>
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <h2 className="text-xl font-bold text-slate-900">Demo thực tiễn</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Luồng demo phục vụ mua sắm thực tế: tìm sản phẩm theo ngân sách, hỏi chính sách sau bán và điều hướng người dùng đến trang
              catalog từ chat.
            </p>
            <Link href="/products" className="btn-secondary mt-4 w-full justify-center">
              Xem catalog sản phẩm
            </Link>
          </section>
        </aside>
      </section>
    </div>
  );
}
