"use client";

import { FormEvent, useState } from "react";
import { MessageCircle, X } from "lucide-react";
import { useUiStore } from "@/store/ui-store";
import { config } from "@/lib/config";
import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";
import { askAi, trackAiEvent } from "@/services/api/ai";
import { getAccessToken } from "@/services/auth";
import { extractUserIdFromJwt } from "@/lib/jwt";

export function ChatWidget() {
  const { chatOpen, setChatOpen } = useUiStore();
  const token = getAccessToken();
  const userId = token ? extractUserIdFromJwt(token) : undefined;
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string }>>([]);
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
      setMessages((prev) => [...prev, { role: "assistant", text: res.answer }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Mình chưa lấy được dữ liệu từ AI service lúc này." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {chatOpen ? (
        <div className="w-[92vw] max-w-sm rounded-2xl border border-border bg-slate-50 p-3 shadow-2xl">
          <div className="mb-2 flex items-center justify-between"><p className="font-semibold">AI Assistant</p><button onClick={() => setChatOpen(false)}><X className="h-4 w-4" /></button></div>
          <div className="mb-2 flex max-h-[28rem] min-h-80 flex-col gap-2 overflow-y-auto rounded-xl bg-white p-2">
            {messages.map((m, i) => <ChatMessageBubble key={i} role={m.role} text={m.text} />)}
            {loading ? <ChatMessageBubble role="assistant" text="Đang suy nghĩ..." /> : null}
          </div>
          <div className="mb-2 flex flex-wrap gap-2">{config.aiSuggestions.slice(0,2).map((s) => <button key={s} onClick={() => setValue(s)} className="rounded-full bg-slate-200 px-2 py-1 text-xs">{s}</button>)}</div>
          <form onSubmit={submit} className="flex gap-2"><input className="w-full rounded-xl border border-border p-2 text-sm" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Nhập câu hỏi..." /><button className="rounded-xl bg-slate-900 px-3 text-sm text-white">Gửi</button></form>
        </div>
      ) : (
        <button onClick={() => setChatOpen(true)} className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-2xl"><MessageCircle className="h-4 w-4" /> Hỏi AI</button>
      )}
    </div>
  );
}
