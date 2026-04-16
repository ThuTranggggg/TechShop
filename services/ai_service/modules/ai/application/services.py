"""
Application layer - Use cases and command handlers.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from django.db import transaction

from modules.ai.domain.entities import (
    BehavioralEvent,
    UserPreferenceProfile,
    KnowledgeDocument,
    KnowledgeChunk,
    ChatSession,
    ChatMessage,
)
from modules.ai.domain.value_objects import (
    EventType,
    PriceRange,
    DocumentType,
    ChatRole,
    ChatIntent,
)
from modules.ai.domain.repositories import (
    BehavioralEventRepository,
    UserPreferenceProfileRepository,
    KnowledgeDocumentRepository,
    KnowledgeChunkRepository,
    ChatSessionRepository,
    ChatMessageRepository,
)
from modules.ai.domain.services import (
    PriceRangeNormalizer,
    PreferenceProfileBuilder,
    RecommendationScorer,
    GraphService,
    RetrievalService,
)
from modules.ai.infrastructure.repositories import (
    DjangoBehavioralEventRepository,
    DjangoUserPreferenceProfileRepository,
    DjangoKnowledgeDocumentRepository,
    DjangoKnowledgeChunkRepository,
    DjangoChatSessionRepository,
    DjangoChatMessageRepository,
    fetch_published_products,
    build_product_catalog_document,
)
from modules.ai.infrastructure.models import KnowledgeDocumentModel
from modules.ai.infrastructure.domain_services import (
    DefaultPriceRangeNormalizer,
    EventBasedPreferenceProfileBuilder,
    SimpleRecommendationScorer,
    MockGraphService,
    SemanticRetrievalService,
)
from modules.ai.infrastructure.providers import (
    get_ai_provider,
)

logger = logging.getLogger(__name__)


class TrackBehavioralEventUseCase:
    """Track a single behavioral event."""

    def __init__(
        self,
        event_repo: Optional[BehavioralEventRepository] = None,
        profile_repo: Optional[UserPreferenceProfileRepository] = None,
        preference_builder: Optional[PreferenceProfileBuilder] = None,
        graph_service: Optional[GraphService] = None,
        price_normalizer: Optional[PriceRangeNormalizer] = None,
    ):
        self.event_repo = event_repo or DjangoBehavioralEventRepository()
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()
        self.preference_builder = preference_builder or EventBasedPreferenceProfileBuilder()
        self.graph_service = graph_service or MockGraphService()
        self.price_normalizer = price_normalizer or DefaultPriceRangeNormalizer()

    def execute(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        brand_name: Optional[str] = None,
        category_name: Optional[str] = None,
        price_amount: Optional[float] = None,
        keyword: Optional[str] = None,
        source_service: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BehavioralEvent:
        """Execute behavioral event tracking."""

        # Normalize price range if price provided
        price_range = None
        if price_amount is not None:
            price_range = self.price_normalizer.normalize_price(price_amount)

        # Create event
        event = BehavioralEvent(
            id=uuid4(),
            event_type=EventType(event_type),
            user_id=user_id,
            session_id=session_id,
            product_id=product_id,
            variant_id=variant_id,
            brand_name=brand_name,
            category_name=category_name,
            price_amount=price_amount,
            price_range=price_range,
            keyword=keyword,
            source_service=source_service,
            occurred_at=datetime.now(),
            metadata=metadata or {},
        )

        # Save event
        saved_event = self.event_repo.add(event)
        logger.info(f"Event tracked: {event_type} for user {user_id}")

        # Update user profile if user_id present
        if user_id:
            try:
                profile = self.profile_repo.get_or_create(user_id)
                profile = self.preference_builder.update_profile_with_event(profile, event)
                profile.last_interaction_at = datetime.now()
                self.profile_repo.save(profile)
                logger.info(f"Profile updated for user {user_id}")
            except Exception as e:
                logger.error(f"Error updating profile: {e}")

        # Sync to graph
        try:
            self.graph_service.sync_event_to_graph(event)
        except Exception as e:
            logger.error(f"Error syncing to graph: {e}")

        return saved_event


class BulkTrackBehavioralEventsUseCase:
    """Track multiple behavioral events in bulk."""

    def __init__(
        self,
        event_repo: Optional[BehavioralEventRepository] = None,
        track_single: Optional[TrackBehavioralEventUseCase] = None,
    ):
        self.event_repo = event_repo or DjangoBehavioralEventRepository()
        self.track_single = track_single or TrackBehavioralEventUseCase()

    def execute(self, events_data: List[Dict[str, Any]]) -> List[BehavioralEvent]:
        """Execute bulk tracking."""
        results = []
        for event_data in events_data:
            result = self.track_single.execute(**event_data)
            results.append(result)
        logger.info(f"Bulk tracked {len(results)} events")
        return results


class RebuildUserPreferenceProfileUseCase:
    """Rebuild user preference profile from all events."""

    def __init__(
        self,
        event_repo: Optional[BehavioralEventRepository] = None,
        profile_repo: Optional[UserPreferenceProfileRepository] = None,
        preference_builder: Optional[PreferenceProfileBuilder] = None,
    ):
        self.event_repo = event_repo or DjangoBehavioralEventRepository()
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()
        self.preference_builder = preference_builder or EventBasedPreferenceProfileBuilder()

    def execute(self, user_id: UUID) -> UserPreferenceProfile:
        """Rebuild profile from all user events."""
        # Get all user events
        events = self.event_repo.get_by_user(user_id, limit=10000)

        # Build fresh profile
        profile = self.preference_builder.build_profile_from_events(user_id, events)

        # Save
        saved_profile = self.profile_repo.save(profile)
        logger.info(f"Profile rebuilt for user {user_id}")
        return saved_profile


class GetUserPreferenceSummaryUseCase:
    """Get user preference summary."""

    def __init__(self, profile_repo: Optional[UserPreferenceProfileRepository] = None):
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()

    def execute(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get preference summary."""
        profile = self.profile_repo.get_by_user_id(user_id)
        if not profile:
            return None

        return {
            "user_id": str(user_id),
            "top_brands": [
                {"brand_name": b.brand_name, "score": b.score, "count": b.interaction_count}
                for b in profile.get_top_brand(5)
            ],
            "top_categories": [
                {"category_name": c.category_name, "score": c.score, "count": c.interaction_count}
                for c in profile.get_top_category(5)
            ],
            "top_price_ranges": [
                {"price_range": p.price_range.value, "score": p.score, "count": p.interaction_count}
                for p in profile.get_top_price_range(5)
            ],
            "recent_keywords": profile.recent_keywords[:10],
            "purchase_intent_score": profile.purchase_intent_score,
            "last_interaction_at": profile.last_interaction_at.isoformat() if profile.last_interaction_at else None,
        }


class GenerateRecommendationsUseCase:
    """Generate personalized recommendations."""

    def __init__(
        self,
        profile_repo: Optional[UserPreferenceProfileRepository] = None,
        scorer: Optional[RecommendationScorer] = None,
    ):
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()
        self.scorer = scorer or SimpleRecommendationScorer()

    def score_products(
        self,
        products: List[Dict[str, Any]],
        user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Score products for user.
        Returns products with scores and reason codes.
        """
        if not user_id:
            # Return unchanged for anonymous
            return products

        profile = self.profile_repo.get_by_user_id(user_id)
        if not profile:
            return products

        scored = []
        for product in products:
            score = self.scorer.score_product_for_user(
                product_id=UUID(product.get("id", "00000000-0000-0000-0000-000000000000")),
                product_brand=product.get("brand", ""),
                product_category=product.get("category", ""),
                product_price=float(product.get("price", 0)),
                user_profile=profile,
            )

            reasons = self.scorer.get_reason_codes(
                product_brand=product.get("brand", ""),
                product_category=product.get("category", ""),
                product_price=float(product.get("price", 0)),
                user_profile=profile,
            )

            scored_product = {**product, "score": score, "reason_codes": reasons}
            scored.append(scored_product)

        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored


class IngestKnowledgeDocumentUseCase:
    """Ingest and process knowledge document."""

    def __init__(
        self,
        doc_repo: Optional[KnowledgeDocumentRepository] = None,
        chunk_repo: Optional[KnowledgeChunkRepository] = None,
        provider = None,
    ):
        self.doc_repo = doc_repo or DjangoKnowledgeDocumentRepository()
        self.chunk_repo = chunk_repo or DjangoKnowledgeChunkRepository()
        self.provider = provider or get_ai_provider()

    @transaction.atomic
    def execute(
        self,
        title: str,
        content: str,
        document_type: str,
        source: str = "internal",
        slug: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest document and create chunks."""

        # Create document
        document = KnowledgeDocument(
            id=uuid4(),
            document_type=DocumentType(document_type),
            title=title,
            slug=slug,
            source=source,
            content=content,
            metadata=metadata or {},
            is_active=True,
        )

        saved_doc = self.doc_repo.add(document)
        logger.info(f"Document created: {title}")

        # Chunk content
        chunks = self._chunk_content(saved_doc.id, content)
        embeddings = self.provider.generate_embeddings([chunk.content for chunk in chunks]) if chunks else []
        for chunk, embedding in zip(chunks, embeddings):
            chunk.metadata["embedding"] = embedding
        saved_chunks = self.chunk_repo.add_bulk(chunks)
        logger.info(f"Created {len(saved_chunks)} chunks")

        return {
            "document_id": str(saved_doc.id),
            "title": saved_doc.title,
            "chunk_count": len(saved_chunks),
        }

    def _chunk_content(self, document_id: UUID, content: str, chunk_size: int = 500) -> List[KnowledgeChunk]:
        """Simple chunking by paragraph."""
        paragraphs = content.split("\n\n")
        chunks = []
        chunk_index = 0

        for para in paragraphs:
            if para.strip():
                chunk = KnowledgeChunk(
                    id=uuid4(),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=para.strip(),
                    metadata={"length": len(para)},
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks


class CreateChatSessionUseCase:
    """Create a new chat session."""

    def __init__(self, session_repo: Optional[ChatSessionRepository] = None):
        self.session_repo = session_repo or DjangoChatSessionRepository()

    def execute(
        self,
        user_id: Optional[UUID] = None,
        session_title: Optional[str] = None,
    ) -> ChatSession:
        """Create chat session."""
        session = ChatSession(
            id=uuid4(),
            user_id=user_id,
            session_title=session_title,
        )
        saved = self.session_repo.create(session)
        logger.info(f"Chat session created: {session.id}")
        return saved


class AppendChatMessageUseCase:
    """Add message to chat session."""

    def __init__(
        self,
        message_repo: Optional[ChatMessageRepository] = None,
        session_repo: Optional[ChatSessionRepository] = None,
    ):
        self.message_repo = message_repo or DjangoChatMessageRepository()
        self.session_repo = session_repo or DjangoChatSessionRepository()

    def execute(
        self,
        session_id: UUID,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Add message."""
        message = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            role=ChatRole(role),
            content=content,
            metadata=metadata or {},
        )
        saved = self.message_repo.add(message)

        # Update session updated_at
        session = self.session_repo.get_by_id(session_id)
        if session:
            session.updated_at = datetime.now()
            self.session_repo.save(session)

        logger.debug(f"Message added to session {session_id}")
        return saved


class GenerateChatAnswerUseCase:
    """Generate answer for chat query."""

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        llm_provider=None,
        session_repo: Optional[ChatSessionRepository] = None,
        message_repo: Optional[ChatMessageRepository] = None,
    ):
        self.retrieval_service = retrieval_service or SemanticRetrievalService()
        self.llm_provider = llm_provider
        self.session_repo = session_repo or DjangoChatSessionRepository()
        self.message_repo = message_repo or DjangoChatMessageRepository()

    def set_llm_provider(self, provider):
        """Set LLM provider."""
        self.llm_provider = provider

    def execute(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        user_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate answer."""
        if not self.llm_provider:
            self.llm_provider = get_ai_provider()

        history = chat_history or []
        if session_id and not history:
            history = [
                {"role": message.role.value, "content": message.content}
                for message in self.message_repo.get_n_latest_by_session(session_id, 6)
            ]

        # Classify intent
        intent = self.llm_provider.classify_intent(query)
        filters = self._build_filters(intent)

        # Retrieve context
        context_chunks = self.retrieval_service.retrieve_relevant_chunks(query, limit=5, filters=filters)
        context = "\n".join([chunk.content for chunk in context_chunks])
        if user_context:
            context = f"{context}\n\nUser context:\n{user_context}"

        if session_id:
            AppendChatMessageUseCase(
                message_repo=self.message_repo,
                session_repo=self.session_repo,
            ).execute(
                session_id=session_id,
                role=ChatRole.USER.value,
                content=query,
                metadata={"user_id": str(user_id) if user_id else None},
            )

        # Generate answer
        answer = self.llm_provider.generate_answer(
            query=query,
            context=context,
            chat_history=history,
            user_context=user_context,
        )

        if session_id:
            AppendChatMessageUseCase(
                message_repo=self.message_repo,
                session_repo=self.session_repo,
            ).execute(
                session_id=session_id,
                role=ChatRole.ASSISTANT.value,
                content=answer,
                metadata={"intent": intent},
            )

        sources = [
            {
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "document_title": chunk.metadata.get("document_title"),
                "document_type": chunk.metadata.get("document_type"),
            }
            for chunk in context_chunks
        ]

        return {
            "answer": answer,
            "intent": intent,
            "sources": sources,
            "mode": "yescale_rag",
            "related_products": self._extract_related_products(context_chunks),
        }

    @staticmethod
    def _build_filters(intent: str) -> Dict[str, Any]:
        if intent == ChatIntent.POLICY_QUESTION.value:
            return {
                "document_types": [
                    DocumentType.RETURN_POLICY.value,
                    DocumentType.PAYMENT_POLICY.value,
                    DocumentType.SHIPPING_POLICY.value,
                    DocumentType.FAQ.value,
                    DocumentType.SUPPORT_ARTICLE.value,
                ]
            }
        if intent == ChatIntent.PRODUCT_SEARCH.value:
            return {"document_types": [DocumentType.PRODUCT_CATALOG.value]}
        if intent == ChatIntent.ORDER_STATUS.value:
            return {"document_types": [DocumentType.SUPPORT_ARTICLE.value, DocumentType.FAQ.value]}
        return {}

    @staticmethod
    def _extract_related_products(chunks: List[KnowledgeChunk]) -> List[Dict[str, Any]]:
        products: Dict[str, Dict[str, Any]] = {}
        for chunk in chunks:
            product_id = chunk.metadata.get("product_id")
            if not product_id or product_id in products:
                continue
            products[product_id] = {
                "product_id": product_id,
                "name": chunk.metadata.get("product_name"),
                "slug": chunk.metadata.get("slug"),
                "brand_name": chunk.metadata.get("brand_name"),
                "category_name": chunk.metadata.get("category_name"),
                "price": chunk.metadata.get("price"),
                "thumbnail_url": chunk.metadata.get("thumbnail_url"),
            }
        return list(products.values())


class SyncProductKnowledgeUseCase:
    """Ingest published catalog products into AI-owned knowledge documents."""

    def __init__(self, ingest_use_case: Optional[IngestKnowledgeDocumentUseCase] = None):
        self.ingest_use_case = ingest_use_case or IngestKnowledgeDocumentUseCase()

    @transaction.atomic
    def execute(self, page_size: int = 100) -> Dict[str, int]:
        products = fetch_published_products(page_size=page_size)
        KnowledgeDocumentModel.objects.filter(
            document_type=DocumentType.PRODUCT_CATALOG.value
        ).delete()

        created = 0
        for product in products:
            document = build_product_catalog_document(product)
            self.ingest_use_case.execute(**document)
            created += 1

        return {"products_indexed": created}
