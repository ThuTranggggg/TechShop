"""
LLM Provider abstraction and implementations.
Supports mock and real LLM backends.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    def classify_intent(self, query: str) -> str:
        """Classify user query intent."""
        pass

    @abstractmethod
    def generate_answer(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate answer based on query and context."""
        pass

    @abstractmethod
    def maybe_extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from query."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for development/testing."""

    # Intent classification rules
    PRODUCT_KEYWORDS = ["sản phẩm", "điện thoại", "laptop", "máy tính", "camera", "nào"]
    ORDER_KEYWORDS = ["đơn hàng", "order", "when", "khi nào"]
    SHIPMENT_KEYWORDS = ["vận chuyển", "giao", "tracking", "ở đâu", "chưa nhận"]
    POLICY_KEYWORDS = ["chính sách", "policy", "đổi", "trả", "return", "exchange"]
    PAYMENT_KEYWORDS = ["thanh toán", "payment", "trả tiền", "giá"]

    def classify_intent(self, query: str) -> str:
        """
        Simple rule-based intent classification.
        Returns: product_search, order_status, shipment_status, policy_question, general_support, unknown
        """
        query_lower = query.lower()

        if any(kw in query_lower for kw in self.ORDER_KEYWORDS):
            if "status" in query_lower or "tình trạng" in query_lower:
                return "order_status"

        if any(kw in query_lower for kw in self.SHIPMENT_KEYWORDS):
            return "shipment_status"

        if any(kw in query_lower for kw in self.POLICY_KEYWORDS):
            return "policy_question"

        if any(kw in query_lower for kw in self.PAYMENT_KEYWORDS):
            return "payment_status"

        if any(kw in query_lower for kw in self.PRODUCT_KEYWORDS):
            return "product_search"

        return "general_support"

    def generate_answer(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate answer using context + templates.
        No hallucination - only uses provided context.
        """
        intent = self.classify_intent(query)

        if not context or context.strip() == "":
            return self._generate_no_context_answer(intent, query)

        # Template-based answer generation
        if intent == "product_search":
            return self._answer_product_query(query, context)
        elif intent == "order_status":
            return self._answer_order_query(query, context, user_context)
        elif intent == "shipment_status":
            return self._answer_shipment_query(query, context, user_context)
        elif intent == "policy_question":
            return self._answer_policy_query(query, context)
        elif intent == "payment_status":
            return self._answer_payment_query(query, context, user_context)
        else:
            return self._answer_general_query(query, context)

    def maybe_extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract brand/category/price mentions from query."""
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

    def _generate_no_context_answer(self, intent: str, query: str) -> str:
        """Generate answer when context is unavailable."""
        if intent == "product_search":
            return "Xin lỗi, tôi chưa có thông tin đủ để trả lời về các sản phẩm cụ thể bây giờ. Bạn có thể tìm kiếm trực tiếp trên cửa hàng hoặc liên hệ với hỗ trợ khách hàng."
        elif intent == "order_status":
            return "Để kiểm tra trạng thái đơn hàng, tôi sẽ cần biết thêm thông tin. Vui lòng cung cấp mã đơn hàng hoặc đơn hàng ID."
        elif intent == "shipment_status":
            return "Tôi chưa có thông tin vận chuyển hiện tại. Vui lòng cung cấp mã theo dõi hoặc mã đơn hàng."
        elif intent == "policy_question":
            return "Chúng tôi chưa cập nhật thông tin chính sách này. Vui lòng liên hệ với bộ phận hỗ trợ để biết thêm chi tiết."
        else:
            return "Tôi hiểu câu hỏi của bạn nhưng chưa có đủ thông tin để trả lời. Bạn có thể liên hệ với hỗ trợ khách hàng để được giúp đỡ."

    def _answer_product_query(self, query: str, context: str) -> str:
        """Answer product-related queries."""
        return f"Dựa trên thông tin có sẵn:\n\n{context}\n\nNếu bạn muốn biết thêm, tôi có thể giúp bạn tìm kiếm thêm sản phẩm phù hợp."

    def _answer_order_query(
        self,
        query: str,
        context: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Answer order-related queries."""
        answer = f"Thông tin đơn hàng:\n\n{context}"
        if user_context and user_context.get("order_reference"):
            answer = f"Đơn hàng {user_context['order_reference']}:\n\n" + answer
        return answer

    def _answer_shipment_query(
        self,
        query: str,
        context: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Answer shipment-related queries."""
        answer = f"Thông tin vận chuyển:\n\n{context}"
        if user_context and user_context.get("shipment_reference"):
            answer = f"Vận chuyển {user_context['shipment_reference']}:\n\n" + answer
        return answer

    def _answer_policy_query(self, query: str, context: str) -> str:
        """Answer policy-related queries."""
        return f"Theo chính sách của chúng tôi:\n\n{context}\n\nNếu bạn có thêm câu hỏi, vui lòng liên hệ hỗ trợ."

    def _answer_payment_query(
        self,
        query: str,
        context: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Answer payment-related queries."""
        return f"Thông tin thanh toán:\n\n{context}"

    def _answer_general_query(self, query: str, context: str) -> str:
        """Answer general queries."""
        return f"Dựa trên thông tin có sẵn:\n\n{context}"


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get appropriate LLM provider."""
    provider_type = os.getenv("LLM_PROVIDER", "mock").lower()

    if provider_type == "openai":
        # Would be real OpenAI implementation
        logger.warning("OpenAI provider not fully implemented, using mock")
        return MockLLMProvider()
    elif provider_type == "anthropic":
        # Would be real Anthropic implementation
        logger.warning("Anthropic provider not fully implemented, using mock")
        return MockLLMProvider()
    else:
        logger.info("Using mock LLM provider")
        return MockLLMProvider()
