from uuid import uuid4
from unittest.mock import patch

from django.test import SimpleTestCase

from modules.ai.application.services import GenerateChatAnswerUseCase
from modules.ai.infrastructure.providers import MockLLMProvider


class StubChunk:
    def __init__(self, document_id, chunk_index, content, metadata):
        self.document_id = document_id
        self.chunk_index = chunk_index
        self.content = content
        self.metadata = metadata


class StubRetrievalService:
    def __init__(self, chunks):
        self.chunks = chunks

    def retrieve_relevant_chunks(self, query: str, limit: int = 5, filters=None):
        return self.chunks[:limit]


class StubRecommendationUseCase:
    def __init__(self, products):
        self.products = products

    def recommend_from_catalog(self, user_id=None, query: str = "", limit: int = 3, entities=None):
        return {"products": self.products[:limit]}


class StubMessageRepo:
    def __init__(self):
        self.messages = []

    def add(self, message):
        self.messages.append(message)
        return message

    def get_n_latest_by_session(self, session_id, limit):
        return []


class StubSessionRepo:
    def __init__(self):
        self.sessions = {}

    def get_by_id(self, session_id):
        return self.sessions.get(session_id)

    def save(self, session):
        self.sessions[session.id] = session
        return session


class StubDocument:
    def __init__(self, title, document_type="faq", source="internal"):
        self.title = title
        self.document_type = type("DocumentTypeValue", (), {"value": document_type})()
        self.source = source


class StubProvider:
    def classify_intent(self, query: str) -> str:
        return "product_search"

    def maybe_extract_entities(self, query: str):
        return {"brands": [], "categories": [], "price_filters": [], "keywords": []}

    def generate_answer(self, query: str, context: str, chat_history=None, user_context=None) -> str:
        if not context:
            raise ValueError("missing context")
        return f"Grounded answer for: {query}"


class OrderStatusProvider(StubProvider):
    def classify_intent(self, query: str) -> str:
        return "order_status"


class RAGChatTests(SimpleTestCase):
    def test_provider_classifies_vietnamese_order_status_queries(self):
        provider = MockLLMProvider()

        self.assertEqual(provider.classify_intent("Trạng thái đơn hàng của tôi thế nào?"), "order_status")

    def test_generate_chat_answer_includes_sources_and_related_products(self):
        chunk = StubChunk(
            document_id=uuid4(),
            chunk_index=0,
            content="Samsung Galaxy A55 under 10 million VND",
            metadata={
                "product_id": "p1",
                "product_name": "Galaxy A55",
                "brand_name": "Samsung",
                "category_name": "Dien thoai",
                "price": 9_990_000,
                "document_title": "Galaxy A55",
            },
        )
        recommended_product = {
            "product_id": "p1",
            "product_name": "Galaxy A55",
            "brand": "Samsung",
            "category": "Dien thoai",
            "price": 9_990_000,
            "score": 98.5,
            "reason_codes": ["preferred_category"],
        }
        use_case = GenerateChatAnswerUseCase(
            retrieval_service=StubRetrievalService([chunk]),
            llm_provider=StubProvider(),
            recommendation_use_case=StubRecommendationUseCase([recommended_product]),
        )

        with patch("modules.ai.application.services.DjangoKnowledgeDocumentRepository.get_by_id", return_value=StubDocument("Galaxy A55")):
            result = use_case.execute(query="Samsung nao duoi 10 trieu?", user_id=uuid4())

        self.assertEqual(result["mode"], "hybrid_rag_graph_lstm")
        self.assertEqual(result["intent"], "product_search")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(len(result["related_products"]), 1)
        self.assertEqual(result["related_products"][0]["product_id"], "p1")

    def test_generate_chat_answer_without_context_raises(self):
        use_case = GenerateChatAnswerUseCase(
            retrieval_service=StubRetrievalService([]),
            llm_provider=StubProvider(),
            recommendation_use_case=StubRecommendationUseCase([]),
        )

        with self.assertRaises(ValueError):
            use_case.execute(query="Xin chao")

    def test_generate_chat_answer_handles_order_context(self):
        chunk = StubChunk(
            document_id=uuid4(),
            chunk_index=0,
            content="Order status guidance only",
            metadata={"document_title": "Order status FAQ", "document_type": "faq"},
        )
        use_case = GenerateChatAnswerUseCase(
            retrieval_service=StubRetrievalService([chunk]),
            llm_provider=OrderStatusProvider(),
            recommendation_use_case=StubRecommendationUseCase([]),
        )

        with patch("modules.ai.application.services.DjangoKnowledgeDocumentRepository.get_by_id", return_value=StubDocument("Order status FAQ")):
            result = use_case.execute(
                query="Trạng thái đơn hàng của tôi thế nào?",
                user_context={"order_number": "ORD-001", "status": "shipping"},
            )

        self.assertEqual(result["intent"], "order_status")
        self.assertEqual(result["sources"][0]["document_title"], "Order status FAQ")
