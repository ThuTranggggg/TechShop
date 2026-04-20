import { apiFetch } from "@/services/api/client";

export type AiSource = {
  document_id: string;
  chunk_index?: number;
  document_title?: string | null;
  document_type?: string | null;
  source?: string | null;
  snippet?: string | null;
};

export type AiRelatedProduct = {
  id: string;
  name: string;
  slug?: string;
  short_description?: string;
  brand_name?: string;
  category_name?: string;
  base_price?: number | string;
  thumbnail_url?: string;
  is_featured?: boolean;
};

export type AiAnswerResponse = {
  session_id?: string;
  answer: string;
  intent?: string;
  mode?: string;
  sources?: AiSource[];
  related_products?: AiRelatedProduct[];
};

export type AiBehaviorSummary = {
  total_events: number;
  unique_users: number;
  event_breakdown: Array<{ event_type: string; count: number }>;
  top_viewed_categories: Array<{ category_name: string; count: number }>;
  top_viewed_products: Array<{ product_id: string; product_name: string; count: number }>;
  conversion_funnel: Array<{ step: string; users: number; rate?: number }>;
  abandoned_cart_sessions: number;
  co_viewed_products: Array<{ pair: string[]; count: number }>;
  co_purchased_products: Array<{ pair: string[]; count: number }>;
  low_intent_users: string[];
  user_segments: Array<{ segment: string; user_count: number }>;
  timeline: Array<{ date: string; count: number }>;
};

export type AiKnowledgeDocument = {
  id: string;
  title: string;
  document_type: string;
  source?: string;
  content_preview?: string;
  created_at?: string;
};

export const getRecommendations = (payload: { user_id?: string; products: Array<Record<string, unknown>>; limit?: number; query?: string }) =>
  apiFetch<{
    products: Array<{
      product_id: string;
      product_name: string;
      brand: string;
      price: number;
      score: number;
      reason?: string;
      explanation?: string;
      reason_codes: string[];
      thumbnail_url?: string;
    }>;
  }>("/ai/api/v1/ai/recommendations/", { method: "POST", body: JSON.stringify(payload) });

export const getPersonalizedRecommendations = (userId: string, limit = 10, query = "") =>
  apiFetch<{
    products: Array<{
      product_id: string;
      product_name: string;
      brand: string;
      category: string;
      price: number;
      score: number;
      reason?: string;
      explanation?: string;
      reason_codes: string[];
      thumbnail_url?: string;
    }>;
    mode: string;
    total_count: number;
    generated_at: string;
  }>(`/ai/api/v1/ai/recommendations/${userId}/?limit=${limit}${query ? `&query=${encodeURIComponent(query)}` : ""}`);

type AiEventType =
  | "search"
  | "product_view"
  | "product_click"
  | "view_category"
  | "add_to_cart"
  | "remove_from_cart"
  | "add_to_wishlist"
  | "checkout_started"
  | "order_created"
  | "order_cancel"
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
  apiFetch<AiAnswerResponse>("/ai/api/v1/ai/chat/ask/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getKnowledgeDocuments = () =>
  apiFetch<{ documents: AiKnowledgeDocument[]; count: number }>("/ai/api/v1/admin/ai/knowledge/");

export const getBehaviorSummary = () => apiFetch<AiBehaviorSummary>("/ai/api/v1/ai/behavior/summary/");

export const getBehaviorFunnel = () =>
  apiFetch<{ steps: Array<{ step: string; users: number; rate?: number }> }>("/ai/api/v1/ai/behavior/funnel/");

export const getBehaviorUser = (userId: string) =>
  apiFetch<{
    user_id: string;
    top_events: Array<{ event_type: string; count: number }>;
    top_categories: Array<{ category_name: string; count: number }>;
    top_products: Array<{ product_id: string; product_name: string; count: number }>;
    recent_timeline: Array<{ occurred_at: string; event_type: string; product_name?: string }>;
    next_likely_actions: string[];
    next_likely_products: Array<{ product_id: string; product_name: string; score: number; reason?: string }>;
  }>(`/ai/api/v1/ai/behavior/users/${userId}/`);

export const aiSearchCatalog = (params: { q: string; user_id?: string; limit?: number }) => {
  const query = new URLSearchParams();
  query.set("q", params.q);
  if (params.user_id) query.set("user_id", params.user_id);
  if (params.limit) query.set("limit", String(params.limit));
  return apiFetch<{ products: AiRelatedProduct[]; total_count: number; generated_at: string }>(`/ai/api/v1/ai/search/?${query.toString()}`);
};

export const aiAddToCart = (payload: { user_id: string; product_id: string; quantity?: number; variant_id?: string }) =>
  apiFetch<Record<string, unknown>>("/ai/api/v1/ai/actions/add-to-cart/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const aiCreateOrder = (payload: { user_id: string; cart_id: string; shipping_address: Record<string, string>; notes?: string }) =>
  apiFetch<Record<string, unknown>>("/ai/api/v1/ai/actions/create-order/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const rebuildKnowledgeGraph = () =>
  apiFetch<{ output: string }>("/ai/api/v1/ai/kg/rebuild/", { method: "POST", body: JSON.stringify({ clear_graph: true }) });

export const trainLstmModel = (payload?: { dataset?: string; epochs?: number; sequence_length?: number; batch_size?: number }) =>
  apiFetch<{ output: string }>("/ai/api/v1/ai/lstm/train/", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });

export const rebuildRagIndex = () =>
  apiFetch<{ output: string }>("/ai/api/v1/ai/rag/rebuild/", { method: "POST", body: JSON.stringify({ replace: true }) });
