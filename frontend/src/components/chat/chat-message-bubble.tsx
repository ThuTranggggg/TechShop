import Link from "next/link";
import { AiRelatedProduct, AiSource } from "@/services/api/ai";

type ChatMessageBubbleProps = {
  role: "user" | "assistant";
  text: string;
  sources?: AiSource[];
  relatedProducts?: AiRelatedProduct[];
};

export function ChatMessageBubble({ role, text, sources, relatedProducts }: ChatMessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${isUser ? "ml-auto bg-slate-900 text-white" : "border border-border bg-white"}`}>
      <p className="whitespace-pre-line leading-6">{text}</p>

      {!isUser && sources?.length ? (
        <div className="mt-3 border-t border-border/70 pt-3">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Nguon tri thuc RAG</p>
          <div className="mt-2 space-y-2">
            {sources.slice(0, 3).map((source) => (
              <article key={`${source.document_id}-${source.chunk_index ?? "source"}`} className="rounded-2xl bg-slate-50 px-3 py-2">
                <p className="font-semibold text-slate-900">{source.document_title || "Tai lieu noi bo"}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {source.document_type || "knowledge"} {source.source ? `• ${source.source}` : ""}
                </p>
                {source.snippet ? <p className="mt-1 text-xs leading-5 text-slate-600">{source.snippet}</p> : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {!isUser && relatedProducts?.length ? (
        <div className="mt-3 border-t border-border/70 pt-3">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">San pham lien quan</p>
          <div className="mt-2 grid gap-2">
            {relatedProducts.slice(0, 3).map((product) => (
              <Link
                key={product.id}
                href={`/products/${product.id}`}
                className="rounded-2xl border border-border bg-slate-50 px-3 py-2 text-slate-900 transition-colors hover:bg-slate-100"
              >
                <p className="font-semibold">{product.name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {product.brand_name || "Nhom product"} {product.base_price ? `• ${new Intl.NumberFormat("vi-VN").format(Number(product.base_price))} đ` : ""}
                </p>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
