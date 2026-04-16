import { apiFetch } from "@/services/api/client";
export const getRecommendations = (payload: { user_id?: string; products: Array<Record<string, unknown>>; limit?: number }) =>
  apiFetch<{ products: Array<{ product_id: string; product_name: string; brand: string; price: number; score: number; reason_codes: string[]; thumbnail_url?: string }> }>("/ai/api/v1/ai/recommendations/", { method: "POST", body: JSON.stringify(payload) });

type AiEventType =
  | "search"
  | "product_view"
  | "product_click"
  | "add_to_cart"
  | "remove_from_cart"
  | "checkout_started"
  | "order_created"
  | "payment_success"
  | "chat_query";

export const trackAiEvent = (payload: {
  event_type: AiEventType;
  user_id?: string;
  product_id?: string;
  brand_name?: string;
  category_name?: string;
  price_amount?: number;
  keyword?: string;
  metadata?: Record<string, unknown>;
}) =>
  apiFetch<{ event_id: string }>("/ai/api/v1/ai/events/track/", {
    method: "POST",
    body: JSON.stringify({ source_service: "frontend", ...payload }),
  });

export const getUserPreferenceSummary = (userId: string) =>
  apiFetch<{
    user_id: string;
    top_brands: Array<{ brand_name: string; score: number; interaction_count?: number; count?: number }>;
    top_categories: Array<{ category_name: string; score: number; interaction_count?: number; count?: number }>;
    purchase_intent_score?: number;
    recent_keywords?: string[];
  }>(`/ai/api/v1/ai/users/${userId}/preferences/`);

export const createChatSession = (user_id?: string) =>
  apiFetch<{ id: string; session_title?: string }>("/ai/api/v1/ai/chat/sessions/", {
    method: "POST",
    body: JSON.stringify({ user_id, session_title: "Shopping Assistant" }),
  });

export const askAi = (payload: { session_id?: string; user_id?: string; query: string; context?: Record<string, unknown> }) =>
  apiFetch<{
    answer: string;
    sources?: Array<{ document_title?: string; document_type?: string; chunk_index?: number }>;
    related_products?: Array<{
      product_id?: string;
      name?: string;
      slug?: string;
      brand_name?: string;
      category_name?: string;
      thumbnail_url?: string;
      price?: number;
    }>;
    mode?: string;
  }>("/ai/api/v1/ai/chat/ask/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
