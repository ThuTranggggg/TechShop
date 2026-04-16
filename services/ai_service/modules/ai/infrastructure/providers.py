"""
AI provider integration for chat completions and embeddings.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict, Any

import httpx

from modules.ai.domain.value_objects import ChatIntent

logger = logging.getLogger(__name__)


class AIProviderError(RuntimeError):
    """Base provider error for ai_service upstream failures."""


class AIConfigurationError(AIProviderError):
    """Raised when required provider configuration is missing."""


class AIUpstreamTimeout(AIProviderError):
    """Raised when the upstream AI provider times out."""


class AIUpstreamError(AIProviderError):
    """Raised when the upstream AI provider returns a non-success response."""


class YescaleAIProvider:
    """Single owner for the OpenAI-compatible Yescale chat and embedding APIs."""

    PRODUCT_KEYWORDS = ["sản phẩm", "điện thoại", "laptop", "máy tính", "camera", "nào"]
    ORDER_KEYWORDS = ["đơn hàng", "order", "when", "khi nào"]
    SHIPMENT_KEYWORDS = ["vận chuyển", "giao", "tracking", "ở đâu", "chưa nhận"]
    POLICY_KEYWORDS = ["chính sách", "policy", "đổi", "trả", "return", "exchange"]
    PAYMENT_KEYWORDS = ["thanh toán", "payment", "trả tiền", "giá"]

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        chat_url: Optional[str] = None,
        embeddings_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout_seconds: float = 20.0,
    ):
        self.api_key = api_key or os.getenv("AI_API_KEY", "")
        self.chat_url = chat_url or os.getenv(
            "AI_CHAT_COMPLETIONS_URL",
            "https://api.yescale.io/v1/chat/completions",
        )
        self.embeddings_url = embeddings_url or os.getenv(
            "AI_EMBEDDINGS_URL",
            "https://api.yescale.io/v1/embeddings",
        )
        self.chat_model = chat_model or os.getenv("AI_CHAT_MODEL", "gpt-5.4-nano")
        self.embedding_model = embedding_model or os.getenv(
            "AI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise AIConfigurationError("AI_API_KEY is required for ai_service")

    def classify_intent(self, query: str) -> str:
        """Keep intent routing deterministic so retrieval filters stay stable."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in self.ORDER_KEYWORDS):
            if "status" in query_lower or "tình trạng" in query_lower:
                return ChatIntent.ORDER_STATUS.value

        if any(kw in query_lower for kw in self.SHIPMENT_KEYWORDS):
            return ChatIntent.SHIPMENT_STATUS.value

        if any(kw in query_lower for kw in self.POLICY_KEYWORDS):
            return ChatIntent.POLICY_QUESTION.value

        if any(kw in query_lower for kw in self.PAYMENT_KEYWORDS):
            return ChatIntent.PAYMENT_STATUS.value

        if any(kw in query_lower for kw in self.PRODUCT_KEYWORDS):
            return ChatIntent.PRODUCT_SEARCH.value

        return ChatIntent.GENERAL_SUPPORT.value

    def generate_answer(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate the final answer with retrieved grounding and optional history."""
        if not context.strip():
            raise AIUpstreamError("No retrieval context available for the query")

        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are the TechShop AI assistant. Answer only from the provided context. "
                    "If the answer is not in the context, say that the information is unavailable. "
                    "Keep answers concise and grounded."
                ),
            }
        ]
        if chat_history:
            messages.extend(chat_history[-6:])
        if user_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"User context: {user_context}",
                }
            )
        messages.append(
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            }
        )

        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": 0.2,
        }
        data = self._post_json(self.chat_url, payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIUpstreamError("Invalid chat completion payload") from exc

    def maybe_extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract lightweight product facets for retrieval hints."""
        entities = {
            "brands": [],
            "categories": [],
            "price_filters": [],
            "keywords": [],
        }

        query_lower = query.lower()

        # Simple brand extraction
        brands = ["samsung", "apple", "iphone", "nokia", "xiaomi", "oppo", "vivo", "realme"]
        for brand in brands:
            if brand in query_lower:
                entities["brands"].append(brand)

        # Simple category extraction
        categories = ["smartphone", "laptop", "camera", "máy tính", "điện thoại", "xe"]
        for cat in categories:
            if cat in query_lower:
                entities["categories"].append(cat)

        # Simple price extraction
        if "dưới 10 triệu" in query_lower or "under 10m" in query_lower:
            entities["price_filters"].append("under_10m")
        elif "dưới 5 triệu" in query_lower or "under 5m" in query_lower:
                entities["price_filters"].append("under_5m")
        elif "trên 20 triệu" in query_lower or "above 20m" in query_lower:
            entities["price_filters"].append("above_20m")

        return entities

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in a single round-trip to the provider."""
        payload = {
            "model": self.embedding_model,
            "input": texts,
        }
        data = self._post_json(self.embeddings_url, payload)
        try:
            return [item["embedding"] for item in data["data"]]
        except (KeyError, TypeError) as exc:
            raise AIUpstreamError("Invalid embeddings payload") from exc

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise AIUpstreamTimeout("AI provider request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise AIUpstreamError(
                f"AI provider error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIUpstreamError(f"AI provider request failed: {exc}") from exc


def get_ai_provider() -> YescaleAIProvider:
    """Return the configured real provider or fail explicitly."""
    provider_type = os.getenv("AI_PROVIDER", "yescale").lower()
    if provider_type != "yescale":
        raise AIConfigurationError(f"Unsupported AI_PROVIDER: {provider_type}")
    logger.info("Using Yescale AI provider")
    return YescaleAIProvider()
