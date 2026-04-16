import type { ReactNode } from "react";
import Link from "next/link";

function renderInline(text: string) {
  const parts: Array<{ type: "text" | "strong" | "link"; value: string; href?: string }> = [];
  const regex = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  for (const match of text.matchAll(regex)) {
    const index = match.index ?? 0;
    if (index > last) parts.push({ type: "text", value: text.slice(last, index) });
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push({ type: "strong", value: token.slice(2, -2) });
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) parts.push({ type: "link", value: linkMatch[1], href: linkMatch[2] });
      else parts.push({ type: "text", value: token });
    }
    last = index + token.length;
  }
  if (last < text.length) parts.push({ type: "text", value: text.slice(last) });

  return parts.map((part, index) => {
    if (part.type === "strong") return <strong key={index} className="font-bold text-slate-950">{part.value}</strong>;
    if (part.type === "link" && part.href) {
      const isInternal = part.href.startsWith("/");
      return isInternal ? (
        <Link key={index} href={part.href} className="font-semibold text-primary underline decoration-primary/40 underline-offset-2">
          {part.value}
        </Link>
      ) : (
        <a key={index} href={part.href} target="_blank" rel="noreferrer" className="font-semibold text-primary underline decoration-primary/40 underline-offset-2">
          {part.value}
        </a>
      );
    }
    return <span key={index}>{part.value}</span>;
  });
}

function renderMarkdown(text: string) {
  const lines = text.split(/\n+/).filter(Boolean);
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(
      <p key={`p-${blocks.length}`} className="whitespace-pre-wrap">
        {renderInline(paragraph.join(" "))}
      </p>
    );
    paragraph = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    if (trimmed.startsWith("- ")) {
      flushParagraph();
      blocks.push(
        <li key={`li-${blocks.length}`} className="ml-5 list-disc whitespace-pre-wrap">
          {renderInline(trimmed.slice(2))}
        </li>
      );
      return;
    }
    paragraph.push(trimmed);
  });
  flushParagraph();
  return blocks;
}

export function ChatMessageBubble({ role, text }: { role: "user" | "assistant"; text: string }) {
  return (
    <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${role === "user" ? "ml-auto bg-slate-900 text-white" : "bg-white border border-border text-slate-700"}`}>
      {renderMarkdown(text)}
    </div>
  );
}
