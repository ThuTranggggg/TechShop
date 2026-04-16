from uuid import uuid4

from django.test import SimpleTestCase

from modules.ai.application.services import GenerateChatAnswerUseCase


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


class StubProvider:
    def classify_intent(self, query: str) -> str:
        return "product_search"

    def generate_answer(self, query: str, context: str, chat_history=None, user_context=None) -> str:
        if not context:
            raise ValueError("missing context")
        return f"Grounded answer for: {query}"


class RAGChatTests(SimpleTestCase):
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
                "price": 9990000,
                "document_title": "Galaxy A55",
            },
        )
        use_case = GenerateChatAnswerUseCase(
            retrieval_service=StubRetrievalService([chunk]),
            llm_provider=StubProvider(),
            session_repo=StubSessionRepo(),
            message_repo=StubMessageRepo(),
        )

        result = use_case.execute(query="Samsung nao duoi 10 trieu?", user_id=uuid4(), session_id=uuid4())

        self.assertEqual(result["mode"], "yescale_rag")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(len(result["related_products"]), 1)
        self.assertEqual(result["related_products"][0]["product_id"], "p1")

    def test_generate_chat_answer_without_context_raises(self):
        use_case = GenerateChatAnswerUseCase(
            retrieval_service=StubRetrievalService([]),
            llm_provider=StubProvider(),
            session_repo=StubSessionRepo(),
            message_repo=StubMessageRepo(),
        )

        with self.assertRaises(ValueError):
            use_case.execute(query="Samsung nao duoi 10 trieu?")
