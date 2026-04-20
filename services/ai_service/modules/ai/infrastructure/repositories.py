"""
Infrastructure repositories.
Concrete repository implementations using Django ORM.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from django.db.models import Q

from modules.ai.domain.entities import (
    BehavioralEvent,
    UserPreferenceProfile,
    KnowledgeDocument,
    KnowledgeChunk,
    ChatSession,
    ChatMessage,
)
from modules.ai.domain.repositories import (
    BehavioralEventRepository,
    UserPreferenceProfileRepository,
    KnowledgeDocumentRepository,
    KnowledgeChunkRepository,
    ChatSessionRepository,
    ChatMessageRepository,
)
from modules.ai.domain.value_objects import (
    EventType,
    PriceRange,
    DocumentType,
    ChatRole,
    BrandPreference,
    CategoryPreference,
    PriceRangePreference,
)
from modules.ai.infrastructure.models import (
    BehavioralEventModel,
    UserPreferenceProfileModel,
    KnowledgeDocumentModel,
    KnowledgeChunkModel,
    ChatSessionModel,
    ChatMessageModel,
)
from modules.ai.infrastructure.taxonomy import normalize_text, tokenize


class DjangoBehavioralEventRepository(BehavioralEventRepository):
    """Django ORM implementation of BehavioralEventRepository."""

    def add(self, event: BehavioralEvent) -> BehavioralEvent:
        """Add a new event."""
        model = BehavioralEventModel(
            id=event.id,
            event_type=event.event_type.value,
            user_id=event.user_id,
            session_id=event.session_id,
            product_id=event.product_id,
            variant_id=event.variant_id,
            brand_name=event.brand_name,
            category_name=event.category_name,
            price_amount=event.price_amount,
            price_range=event.price_range.value if event.price_range else None,
            keyword=event.keyword,
            source_service=event.source_service,
            occurred_at=event.occurred_at,
            metadata=event.metadata,
        )
        model.save()
        return self._model_to_entity(model)

    def add_bulk(self, events: List[BehavioralEvent]) -> List[BehavioralEvent]:
        """Add multiple events in bulk."""
        models = [
            BehavioralEventModel(
                id=event.id,
                event_type=event.event_type.value,
                user_id=event.user_id,
                session_id=event.session_id,
                product_id=event.product_id,
                variant_id=event.variant_id,
                brand_name=event.brand_name,
                category_name=event.category_name,
                price_amount=event.price_amount,
                price_range=event.price_range.value if event.price_range else None,
                keyword=event.keyword,
                source_service=event.source_service,
                occurred_at=event.occurred_at,
                metadata=event.metadata,
            )
            for event in events
        ]
        BehavioralEventModel.objects.bulk_create(models)
        return [self._model_to_entity(m) for m in models]

    def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BehavioralEvent]:
        """Get events for a specific user."""
        queryset = BehavioralEventModel.objects.filter(user_id=user_id)
        queryset = queryset.order_by("-occurred_at")[offset : offset + limit]
        return [self._model_to_entity(m) for m in queryset]

    def get_recent_by_user(self, user_id: UUID, limit: int = 50) -> List[BehavioralEvent]:
        """Get recent events for a user."""
        queryset = BehavioralEventModel.objects.filter(user_id=user_id)
        queryset = queryset.order_by("-occurred_at")[:limit]
        return [self._model_to_entity(m) for m in queryset]

    def get_by_product(self, product_id: UUID, limit: int = 100) -> List[BehavioralEvent]:
        """Get events related to a specific product."""
        queryset = BehavioralEventModel.objects.filter(product_id=product_id)
        queryset = queryset.order_by("-occurred_at")[:limit]
        return [self._model_to_entity(m) for m in queryset]

    @staticmethod
    def _model_to_entity(model: BehavioralEventModel) -> BehavioralEvent:
        """Convert model to entity."""
        return BehavioralEvent(
            id=model.id,
            event_type=EventType(model.event_type),
            user_id=model.user_id,
            session_id=model.session_id,
            product_id=model.product_id,
            variant_id=model.variant_id,
            brand_name=model.brand_name,
            category_name=model.category_name,
            price_amount=float(model.price_amount) if model.price_amount is not None else None,
            price_range=PriceRange(model.price_range) if model.price_range else None,
            keyword=model.keyword,
            source_service=model.source_service,
            occurred_at=model.occurred_at,
            metadata=model.metadata,
            created_at=model.created_at,
        )


class DjangoUserPreferenceProfileRepository(UserPreferenceProfileRepository):
    """Django ORM implementation of UserPreferenceProfileRepository."""

    def get_or_create(self, user_id: UUID) -> UserPreferenceProfile:
        """Get or create profile for a user."""
        model, _ = UserPreferenceProfileModel.objects.get_or_create(user_id=user_id)
        return self._model_to_entity(model)

    def save(self, profile: UserPreferenceProfile) -> UserPreferenceProfile:
        """Save/update a profile."""
        model, _ = UserPreferenceProfileModel.objects.get_or_create(
            user_id=profile.user_id,
            defaults={"id": profile.id}
        )
        model.preferred_brands = [
            {"brand_name": b.brand_name, "score": b.score, "interaction_count": b.interaction_count}
            for b in profile.preferred_brands
        ]
        model.preferred_categories = [
            {"category_name": c.category_name, "score": c.score, "interaction_count": c.interaction_count}
            for c in profile.preferred_categories
        ]
        model.preferred_price_ranges = [
            {"price_range": p.price_range.value, "score": p.score, "interaction_count": p.interaction_count}
            for p in profile.preferred_price_ranges
        ]
        model.recent_keywords = profile.recent_keywords
        model.preference_score_summary = profile.preference_score_summary
        model.purchase_intent_score = profile.purchase_intent_score
        model.last_interaction_at = profile.last_interaction_at
        model.save()
        return self._model_to_entity(model)

    def get_by_user_id(self, user_id: UUID) -> Optional[UserPreferenceProfile]:
        """Get profile for a user."""
        try:
            model = UserPreferenceProfileModel.objects.get(user_id=user_id)
            return self._model_to_entity(model)
        except UserPreferenceProfileModel.DoesNotExist:
            return None

    def rebuild_profile_from_events(self, user_id: UUID) -> UserPreferenceProfile:
        """Rebuild profile from all user events."""
        # This will be implemented by application services
        raise NotImplementedError("Use application service instead")

    @staticmethod
    def _model_to_entity(model: UserPreferenceProfileModel) -> UserPreferenceProfile:
        """Convert model to entity."""
        preferred_brands = [
            BrandPreference(
                brand_name=b["brand_name"],
                score=b["score"],
                interaction_count=b["interaction_count"],
            )
            for b in model.preferred_brands
        ]
        preferred_categories = [
            CategoryPreference(
                category_name=c["category_name"],
                score=c["score"],
                interaction_count=c["interaction_count"],
            )
            for c in model.preferred_categories
        ]
        preferred_price_ranges = [
            PriceRangePreference(
                price_range=PriceRange(p["price_range"]),
                score=p["score"],
                interaction_count=p["interaction_count"],
            )
            for p in model.preferred_price_ranges
        ]

        return UserPreferenceProfile(
            id=model.id,
            user_id=model.user_id,
            preferred_brands=preferred_brands,
            preferred_categories=preferred_categories,
            preferred_price_ranges=preferred_price_ranges,
            recent_keywords=model.recent_keywords,
            preference_score_summary=model.preference_score_summary,
            purchase_intent_score=model.purchase_intent_score,
            last_interaction_at=model.last_interaction_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class DjangoKnowledgeDocumentRepository(KnowledgeDocumentRepository):
    """Django ORM implementation of KnowledgeDocumentRepository."""

    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Add a new document."""
        model = KnowledgeDocumentModel(
            id=document.id,
            document_type=document.document_type.value,
            title=document.title,
            slug=document.slug,
            source=document.source,
            content=document.content,
            metadata=document.metadata,
            is_active=document.is_active,
        )
        model.save()
        return self._model_to_entity(model)

    def save(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Save/update a document."""
        model, _ = KnowledgeDocumentModel.objects.get_or_create(id=document.id)
        model.document_type = document.document_type.value
        model.title = document.title
        model.slug = document.slug
        model.source = document.source
        model.content = document.content
        model.metadata = document.metadata
        model.is_active = document.is_active
        model.save()
        return self._model_to_entity(model)

    def get_by_id(self, document_id: UUID) -> Optional[KnowledgeDocument]:
        """Get document by ID."""
        try:
            model = KnowledgeDocumentModel.objects.get(id=document_id)
            return self._model_to_entity(model)
        except KnowledgeDocumentModel.DoesNotExist:
            return None

    def get_active_documents(self, limit: int = 100) -> List[KnowledgeDocument]:
        """Get all active documents."""
        queryset = KnowledgeDocumentModel.objects.filter(is_active=True)
        queryset = queryset.order_by("-created_at")[:limit]
        return [self._model_to_entity(m) for m in queryset]

    def search_by_type(self, document_type: str) -> List[KnowledgeDocument]:
        """Search documents by type."""
        queryset = KnowledgeDocumentModel.objects.filter(
            document_type=document_type,
            is_active=True
        )
        return [self._model_to_entity(m) for m in queryset]

    def delete(self, document_id: UUID) -> None:
        """Delete a document."""
        KnowledgeDocumentModel.objects.filter(id=document_id).delete()

    @staticmethod
    def _model_to_entity(model: KnowledgeDocumentModel) -> KnowledgeDocument:
        """Convert model to entity."""
        return KnowledgeDocument(
            id=model.id,
            document_type=DocumentType(model.document_type),
            title=model.title,
            slug=model.slug,
            source=model.source,
            content=model.content,
            metadata=model.metadata,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class DjangoKnowledgeChunkRepository(KnowledgeChunkRepository):
    """Django ORM implementation of KnowledgeChunkRepository."""

    def add(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """Add a new chunk."""
        model = KnowledgeChunkModel(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            embedding_ref=chunk.embedding_ref,
            metadata=chunk.metadata,
        )
        model.save()
        return self._model_to_entity(model)

    def add_bulk(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Add multiple chunks."""
        models = [
            KnowledgeChunkModel(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding_ref=chunk.embedding_ref,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]
        KnowledgeChunkModel.objects.bulk_create(models)
        return [self._model_to_entity(m) for m in models]

    def get_by_document(self, document_id: UUID) -> List[KnowledgeChunk]:
        """Get all chunks for a document."""
        queryset = KnowledgeChunkModel.objects.filter(document_id=document_id)
        queryset = queryset.order_by("chunk_index")
        return [self._model_to_entity(m) for m in queryset]

    def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        count, _ = KnowledgeChunkModel.objects.filter(document_id=document_id).delete()
        return count

    def search_similar(self, query: str, limit: int = 5) -> List[KnowledgeChunk]:
        """Search similar chunks using broad keyword matching with graceful fallback."""
        try:
            base_queryset = (
                KnowledgeChunkModel.objects.filter(document__is_active=True)
                .select_related("document")
                .defer("embedding")
            )
            normalized_query = normalize_text(query)
            query_tokens = [token for token in tokenize(query) if len(token) > 1]

            if not normalized_query and not query_tokens:
                queryset = base_queryset.order_by("-document__updated_at", "chunk_index")[:limit]
                return [self._model_to_entity(m) for m in queryset]

            filters = Q()
            if normalized_query:
                filters |= Q(content__icontains=query)
                filters |= Q(document__title__icontains=query)

            for token in query_tokens[:8]:
                filters |= Q(content__icontains=token)
                filters |= Q(document__title__icontains=token)
                filters |= Q(document__metadata__icontains=token)
                filters |= Q(metadata__icontains=token)

            queryset = base_queryset.filter(filters).order_by("-document__updated_at", "chunk_index")[: max(limit * 4, limit)]
            results = [self._model_to_entity(model) for model in queryset]
            if results:
                return results

            fallback_queryset = base_queryset.order_by("-document__updated_at", "chunk_index")[:limit]
            return [self._model_to_entity(model) for model in fallback_queryset]
        except Exception as exc:
            logger.warning("Knowledge chunk retrieval failed, falling back to text docs: %s", exc)
            return self._fallback_search_from_documents(query, limit)

    def _fallback_search_from_documents(self, query: str, limit: int) -> List[KnowledgeChunk]:
        """Return text-only fallback chunks when the vector-backed table cannot be queried."""
        base_queryset = KnowledgeDocumentModel.objects.filter(is_active=True)
        normalized_query = normalize_text(query)
        query_tokens = [token for token in tokenize(query) if len(token) > 1]

        if not normalized_query and not query_tokens:
            docs = base_queryset.order_by("-updated_at", "-created_at")[:limit]
        else:
            filters = Q()
            if normalized_query:
                filters |= Q(title__icontains=query)
                filters |= Q(content__icontains=query)
                filters |= Q(metadata__icontains=query)

            for token in query_tokens[:8]:
                filters |= Q(title__icontains=token)
                filters |= Q(content__icontains=token)
                filters |= Q(metadata__icontains=token)

            docs = base_queryset.filter(filters).order_by("-updated_at", "-created_at")[: max(limit * 4, limit)]
            if not docs:
                docs = base_queryset.order_by("-updated_at", "-created_at")[:limit]

        fallback_chunks: List[KnowledgeChunk] = []
        for index, doc in enumerate(docs):
            fallback_chunks.append(
                KnowledgeChunk(
                    id=uuid4(),
                    document_id=doc.id,
                    chunk_index=index,
                    content=doc.content,
                    embedding_ref=doc.source,
                    metadata={
                        **(doc.metadata or {}),
                        "document_type": doc.document_type,
                        "source": doc.source,
                        "title": doc.title,
                    },
                    created_at=doc.created_at,
                )
            )
        return fallback_chunks

    @staticmethod
    def _model_to_entity(model: KnowledgeChunkModel) -> KnowledgeChunk:
        """Convert model to entity."""
        return KnowledgeChunk(
            id=model.id,
            document_id=model.document_id,
            chunk_index=model.chunk_index,
            content=model.content,
            embedding_ref=model.embedding_ref,
            metadata=model.metadata,
            created_at=model.created_at,
        )


class DjangoChatSessionRepository(ChatSessionRepository):
    """Django ORM implementation of ChatSessionRepository."""

    def create(self, session: ChatSession) -> ChatSession:
        """Create a new session."""
        model = ChatSessionModel(
            id=session.id,
            user_id=session.user_id,
            session_title=session.session_title,
        )
        model.save()
        return self._model_to_entity(model)

    def get_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        """Get session by ID."""
        try:
            model = ChatSessionModel.objects.get(id=session_id)
            return self._model_to_entity(model)
        except ChatSessionModel.DoesNotExist:
            return None

    def get_by_user(self, user_id: UUID, limit: int = 20) -> List[ChatSession]:
        """Get sessions for a user."""
        queryset = ChatSessionModel.objects.filter(user_id=user_id)
        queryset = queryset.order_by("-updated_at")[:limit]
        return [self._model_to_entity(m) for m in queryset]

    def save(self, session: ChatSession) -> ChatSession:
        """Save/update a session."""
        model, _ = ChatSessionModel.objects.get_or_create(id=session.id)
        model.user_id = session.user_id
        model.session_title = session.session_title
        model.save()
        return self._model_to_entity(model)

    @staticmethod
    def _model_to_entity(model: ChatSessionModel) -> ChatSession:
        """Convert model to entity."""
        return ChatSession(
            id=model.id,
            user_id=model.user_id,
            session_title=model.session_title,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class DjangoChatMessageRepository(ChatMessageRepository):
    """Django ORM implementation of ChatMessageRepository."""

    def add(self, message: ChatMessage) -> ChatMessage:
        """Add a message."""
        model = ChatMessageModel(
            id=message.id,
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            metadata=message.metadata,
        )
        model.save()
        return self._model_to_entity(model)

    def get_by_session(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ChatMessage]:
        """Get messages for a session."""
        queryset = ChatMessageModel.objects.filter(session_id=session_id)
        queryset = queryset.order_by("created_at")[offset : offset + limit]
        return [self._model_to_entity(m) for m in queryset]

    def get_n_latest_by_session(self, session_id: UUID, n: int = 10) -> List[ChatMessage]:
        """Get n latest messages from session."""
        queryset = ChatMessageModel.objects.filter(session_id=session_id)
        queryset = queryset.order_by("-created_at")[:n]
        # Return in chronological order
        return [self._model_to_entity(m) for m in reversed(list(queryset))]

    @staticmethod
    def _model_to_entity(model: ChatMessageModel) -> ChatMessage:
        """Convert model to entity."""
        return ChatMessage(
            id=model.id,
            session_id=model.session_id,
            role=ChatRole(model.role),
            content=model.content,
            metadata=model.metadata,
            created_at=model.created_at,
        )
