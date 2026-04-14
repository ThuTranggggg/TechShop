export function ChatMessageBubble({ role, text }: { role: "user" | "assistant"; text: string }) {
  return <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${role === "user" ? "ml-auto bg-slate-900 text-white" : "bg-white border border-border"}`}>{text}</div>;
}
