"use client";

import { FormEvent, useState } from "react";
import { config } from "@/lib/config";
import { askAi, createChatSession, trackAiEvent } from "@/services/api/ai";
import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";

export default function ChatPage() {
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string }>>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

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
      const answer = await askAi({ session_id: sid, query: text, user_id: userId });
      trackAiEvent({ event_type: "chat_query", user_id: userId, keyword: text, metadata: { session_id: sid } }).catch(() => undefined);
      setMessages((prev) => [...prev, { role: "assistant", text: answer.answer }]);
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
      <div className="mt-4 flex min-h-[560px] flex-col gap-3 rounded-2xl bg-slate-50 p-4">{messages.map((m, i) => <ChatMessageBubble key={i} role={m.role} text={m.text} />)}{loading ? <ChatMessageBubble role="assistant" text="Dang phan tich..." /> : null}</div>
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2"><input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full rounded-xl border border-border p-3" placeholder="Nhap cau hoi..." /><button className="rounded-xl bg-slate-900 px-5 text-sm font-semibold text-white">Gui</button></form>
    </div>
  );
}
