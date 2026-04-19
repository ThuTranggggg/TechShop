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
  "Tu van mot routine cham soc da duoi 500 nghin.",
  "Chinh sach doi tra cua TechShop nhu the nao?",
  "Can goi y mot bo do cam trai cho cuoi tuan.",
];

const ragSteps = [
  "Nguoi dung dat cau hoi ve san pham, don hang hoac chinh sach.",
  "AI phan loai intent, trich xuat nhom product, danh muc va muc gia roi tim tai lieu lien quan.",
  "He thong hop nhat context tu catalog + knowledge base roi sinh cau tra loi trong chat.",
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
        title: "Deep Model",
        description: "AI service phan loai y dinh, trich xuat thuc the va sinh cau tra loi tu ngu canh da truy hoi.",
        icon: Bot,
      },
      {
        title: "Knowledge Base",
        description: `${knowledgeCount} tai lieu tri thuc dang san sang cho shipping, payment, return policy va huong dan.`,
        icon: Database,
      },
      {
        title: "RAG + Chat",
        description: "Moi cau tra loi co the hien thi tai lieu nguon va goi y san pham lien quan ngay trong khung chat.",
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
          text: "AI service tam thoi chua phan hoi. Ban co the thu lai voi mot cau hoi ngan hon.",
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
              AI Service Demo
            </span>
            <h1 className="mt-4 text-3xl font-black text-slate-900 md:text-5xl">RAG chatbot cho bai toan tu van mua hang thuc te.</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              Trang nay cho thay day du 3 thanh phan: mo hinh AI, knowledge base va quy trinh RAG + chat. Ban co the dat cau hoi,
              xem tai lieu nguon ma AI da truy hoi, va mo nhanh san pham lien quan ngay trong phan hoi.
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
              <h2 className="text-2xl font-bold text-slate-900">AI Shopping Assistant</h2>
              <p className="mt-1 text-sm text-slate-600">Hoi ve san pham, don hang, thanh toan, doi tra va chinh sach giao hang.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary">Model-backed</span>
              <span className="rounded-full bg-accent/10 px-3 py-1 text-accent">{knowledgeCount} KB docs</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">RAG + catalog retrieval</span>
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
                <h3 className="mt-4 text-xl font-bold text-slate-900">San sang demo RAG + Chat</h3>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">
                  Hay hoi ve my pham, me va be, do gia dung, chinh sach doi tra, thanh toan hoac logistics. Cac phan hoi se hien thi tai
                  lieu tri thuc duoc truy hoi khi co.
                </p>
              </div>
            )}
            {loading ? <ChatMessageBubble role="assistant" text="Dang truy hoi tri thuc va tong hop cau tra loi..." /> : null}
          </div>

          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full"
              placeholder="Nhap cau hoi de bat dau demo AI..."
              aria-label="Nhap cau hoi cho AI"
            />
            <button type="submit" className="btn-primary h-12 px-6" disabled={loading}>
              Gui cau hoi
            </button>
          </form>
        </div>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <h2 className="text-xl font-bold text-slate-900">Quy trinh RAG</h2>
            <div className="mt-4 space-y-3">
              {ragSteps.map((step, index) => (
                <article key={step} className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Buoc {index + 1}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{step}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Knowledge Base</h2>
                <p className="mt-1 text-sm text-slate-600">Nguon tri thuc noi bo ma chatbot dang dung de truy hoi.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{knowledgeCount} tai lieu</span>
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
                  Chua tai duoc danh sach tri thuc. Neu backend chua seed du lieu, hay chay seeding de hien thi day du.
                </p>
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-border bg-card p-5 shadow-soft">
            <h2 className="text-xl font-bold text-slate-900">Demo thuc tien</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Luong demo phuc vu mua sam thuc te: tim san pham theo ngan sach, hoi chinh sach sau ban va dieu huong nguoi dung den trang
              catalog tu chat.
            </p>
            <Link href="/products" className="btn-secondary mt-4 w-full justify-center">
              Xem catalog san pham
            </Link>
          </section>
        </aside>
      </section>
    </div>
  );
}
