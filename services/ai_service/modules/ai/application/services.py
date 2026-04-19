"""
Application layer - Use cases and command handlers.
"""
import logging
import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

import httpx
from django.utils import timezone

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
    DocumentType,
    ChatRole,
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
)
from modules.ai.infrastructure.domain_services import (
    DefaultPriceRangeNormalizer,
    EventBasedPreferenceProfileBuilder,
    SimpleRecommendationScorer,
    SimpleRetrievalService,
    get_graph_service,
    get_sequence_service,
)
from modules.ai.infrastructure.providers import get_llm_provider
from modules.ai.infrastructure.taxonomy import normalize_text

logger = logging.getLogger(__name__)


class ProductCatalogLookupService:
    """Fetch and filter product catalog data for AI chat answers."""

    DEFAULT_BASE_URL = os.getenv("PRODUCT_SERVICE_URL", os.getenv("PRODUCT_SERVICE_HOST_URL", "http://host.docker.internal:8002")).rstrip("/")
    FALLBACK_BASE_URLS = [
        os.getenv("PRODUCT_SERVICE_HOST_URL", "http://host.docker.internal:8002").rstrip("/"),
        os.getenv("PRODUCT_SERVICE_PUBLIC_URL", "http://localhost:8002").rstrip("/"),
        os.getenv("PRODUCT_SERVICE_INTERNAL_URL", "http://product_service:8002").rstrip("/"),
        os.getenv("PRODUCT_SERVICE_GATEWAY_URL", "http://gateway/product").rstrip("/"),
    ]

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    def search_products(self, query: str, limit: int = 5, entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Return product candidates filtered by extracted entities."""
        candidates = self._fetch_catalog_page(query=query, page_size=max(limit * 5, 20))
        if not candidates:
            candidates = self._fetch_catalog_page(query="", page_size=100)

        filtered = self._filter_products(candidates, query=query, entities=entities or {})
        return filtered[:limit]

    def get_catalog_snapshot(self, page_size: int = 200) -> List[Dict[str, Any]]:
        """Return a larger catalog snapshot for analytics, KG and RAG jobs."""
        return self._fetch_catalog_page(query="", page_size=page_size)

    def _fetch_catalog_page(self, query: str, page_size: int) -> List[Dict[str, Any]]:
        params = {"page_size": str(page_size)}
        if query:
            params["search"] = query

        candidate_urls = []
        for base_url in [self.base_url, *self.FALLBACK_BASE_URLS]:
            if base_url and base_url not in candidate_urls:
                candidate_urls.append(base_url)

        last_exception = None
        for base_url in candidate_urls:
            url = f"{base_url}/api/v1/catalog/products/"
            try:
                headers = {}
                if "product_service" in base_url:
                    headers["Host"] = "product_service"
                elif "gateway" in base_url:
                    headers["Host"] = "gateway"
                elif "host.docker.internal" in base_url or "localhost" in base_url:
                    headers["Host"] = "localhost"

                with httpx.Client(timeout=self.timeout, headers=headers) as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                return payload.get("results", []) if isinstance(payload, dict) else []
            except Exception as exc:
                last_exception = exc
                logger.warning("Product catalog lookup failed for %s query '%s': %s", base_url, query, exc)

        logger.warning("Product catalog lookup exhausted fallbacks for query '%s': %s", query, last_exception)
        return []

    def _filter_products(self, products: List[Dict[str, Any]], query: str, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        brands = {brand.lower() for brand in entities.get("brands", [])}
        categories = {category.lower() for category in entities.get("categories", [])}
        keyword_terms = self._build_keyword_terms(query, entities)
        price_filters = entities.get("price_filters", [])

        filtered = []
        for product in products:
            brand_name = self._normalize_text(str(product.get("brand_name", "")))
            category_name = self._normalize_text(str(product.get("category_name", "")))
            searchable = self._normalize_text(" ".join(
                str(product.get(key, ""))
                for key in ("name", "short_description", "brand_name", "category_name", "product_type_name")
            ))

            if brands and not any(brand in brand_name or brand in searchable for brand in brands):
                continue

            if categories and not any(category in category_name or category in searchable for category in categories):
                continue

            if keyword_terms and not any(term in searchable for term in keyword_terms):
                continue

            if not self._matches_price_filters(product, price_filters):
                continue

            filtered.append(product)

        if filtered:
            return sorted(filtered, key=self._sort_key)

        # Fallback: loose match on keywords only if strict filters yielded nothing.
        if keyword_terms:
            fallback = [p for p in products if any(term in " ".join(
                str(p.get(key, "")) for key in ("name", "short_description", "brand_name", "category_name", "product_type_name")
            ).lower() for term in keyword_terms)]
            if fallback:
                return sorted(fallback, key=self._sort_key)

        return sorted(products, key=self._sort_key)

    @staticmethod
    def _build_keyword_terms(query: str, entities: Dict[str, Any]) -> List[str]:
        stop_words = {
            "toi", "tôi", "can", "cần", "muon", "muốn", "nao", "nào", "duoi", "dưới", "tren", "trên",
            "gia", "giá", "bao", "nhiêu", "co", "có", "may", "hãy", "giup", "giúp", "tim", "tìm", "cho",
            "minh", "mình", "san", "pham", "sản", "phẩm", "loai", "loại", "hang", "hãng", "budget", "nhom",
            "product",
            "8g", "8gb", "16g", "16gb", "32g", "32gb", "64g", "64gb", "128g", "128gb", "256g", "256gb",
        }
        words = [
            ProductCatalogLookupService._normalize_text(token.strip(" ?!,."))
            for token in query.lower().split()
            if ProductCatalogLookupService._normalize_text(token.strip(" ?!,."))
            and ProductCatalogLookupService._normalize_text(token.strip(" ?!,.")) not in stop_words
        ]
        words.extend(entities.get("brands", []))
        words.extend(entities.get("categories", []))
        seen = []
        for word in words:
            if word not in seen:
                seen.append(word)
        return seen

    @staticmethod
    def _matches_price_filters(product: Dict[str, Any], price_filters: List[str]) -> bool:
        if not price_filters:
            return True

        try:
            price = float(product.get("base_price", 0) or 0)
        except (TypeError, ValueError):
            return False

        for price_filter in price_filters:
            if price_filter == "under_1m" and price >= 1_000_000:
                return False
            if price_filter == "under_3m" and price >= 3_000_000:
                return False
            if price_filter == "under_10m" and price >= 10_000_000:
                return False
            if price_filter == "under_5m" and price >= 5_000_000:
                return False
            if price_filter == "above_20m" and price <= 20_000_000:
                return False
        return True

    @staticmethod
    def _sort_key(product: Dict[str, Any]) -> Any:
        try:
            price = float(product.get("base_price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        return (
            0 if product.get("is_featured") else 1,
            price,
            str(product.get("name", "")).lower(),
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        return normalize_text(text)


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
        self.graph_service = graph_service or get_graph_service()
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
        occurred_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BehavioralEvent:
        """Execute behavioral event tracking."""

        # Normalize price range if price provided
        price_range = None
        if price_amount:
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
            occurred_at=occurred_at or timezone.now(),
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
                profile.last_interaction_at = event.occurred_at or timezone.now()
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

    def __init__(
        self,
        profile_repo: Optional[UserPreferenceProfileRepository] = None,
        graph_service: Optional[GraphService] = None,
    ):
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()
        self.graph_service = graph_service or get_graph_service()

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
            "graph_top_brands": [
                {"brand_name": brand_name, "score": score}
                for brand_name, score in self.graph_service.get_user_top_brands(user_id, 5)
            ],
            "graph_top_categories": [
                {"category_name": category_name, "score": score}
                for category_name, score in self.graph_service.get_user_top_categories(user_id, 5)
            ],
        }


class GenerateRecommendationsUseCase:
    """Generate personalized recommendations."""

    def __init__(
        self,
        event_repo: Optional[BehavioralEventRepository] = None,
        profile_repo: Optional[UserPreferenceProfileRepository] = None,
        scorer: Optional[RecommendationScorer] = None,
        graph_service: Optional[GraphService] = None,
        retrieval_service: Optional[RetrievalService] = None,
        product_lookup_service: Optional[ProductCatalogLookupService] = None,
    ):
        self.event_repo = event_repo or DjangoBehavioralEventRepository()
        self.profile_repo = profile_repo or DjangoUserPreferenceProfileRepository()
        self.scorer = scorer or SimpleRecommendationScorer()
        self.graph_service = graph_service or get_graph_service()
        self.retrieval_service = retrieval_service or SimpleRetrievalService()
        self.product_lookup_service = product_lookup_service or ProductCatalogLookupService()
        self.sequence_service = get_sequence_service()

    def score_products(
        self,
        products: List[Dict[str, Any]],
        user_id: Optional[UUID] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Score products with a hybrid model: profile + LSTM + graph + retrieval."""
        profile = self.profile_repo.get_by_user_id(user_id) if user_id else None
        recent_events = self.event_repo.get_recent_by_user(user_id, limit=10) if user_id else []

        scored = []
        for product in products:
            normalized_product = self._normalize_product(product)
            self._sync_candidate_to_graph(normalized_product)

            component_scores = self._build_component_scores(
                normalized_product,
                user_id=user_id,
                user_profile=profile,
                recent_events=recent_events,
                query=query,
            )
            final_score = self._blend_component_scores(component_scores, user_id=user_id, has_query=bool(query))
            reason_codes = self._build_reason_codes(normalized_product, profile, component_scores)

            scored_product = {
                **normalized_product,
                "score": final_score,
                "reason_codes": reason_codes,
                "reason": self._build_reason_text(reason_codes),
                "component_scores": component_scores,
                "explanation": self._build_explanation(component_scores, reason_codes),
            }
            scored.append(scored_product)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def recommend_from_catalog(
        self,
        user_id: Optional[UUID] = None,
        query: str = "",
        limit: int = 10,
        entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch catalog candidates, score them, and return top recommendations."""
        candidates = self.product_lookup_service.search_products(
            query=query,
            limit=max(limit * 5, 20),
            entities=entities or {},
        )
        scored_products = self.score_products(candidates, user_id=user_id, query=query)
        return {
            "products": scored_products[:limit],
            "total_count": len(scored_products[:limit]),
            "mode": "hybrid_personalized" if user_id else "hybrid_catalog",
            "generated_at": timezone.now().isoformat(),
        }

    def _normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(product.get("id") or product.get("product_id") or "")
        product_name = product.get("name") or product.get("product_name") or "Unknown Product"
        brand = product.get("brand_name") or product.get("brand") or ""
        category = product.get("category_name") or product.get("category") or ""
        price = float(product.get("price") or product.get("base_price") or 0)
        normalized = {
            **product,
            "id": product_id,
            "product_id": product_id,
            "name": product_name,
            "product_name": product_name,
            "brand": brand,
            "brand_name": brand,
            "category": category,
            "category_name": category,
            "price": price,
            "thumbnail_url": product.get("thumbnail_url"),
        }
        return normalized

    def _build_component_scores(
        self,
        product: Dict[str, Any],
        user_id: Optional[UUID],
        user_profile: Optional[UserPreferenceProfile],
        recent_events: List[BehavioralEvent],
        query: Optional[str],
    ) -> Dict[str, float]:
        product_uuid = _safe_uuid(product.get("id"))
        profile_score = 0.0
        if user_profile and product_uuid:
            profile_score = self.scorer.score_product_for_user(
                product_id=product_uuid,
                product_brand=product.get("brand", ""),
                product_category=product.get("category", ""),
                product_price=float(product.get("price", 0)),
                user_profile=user_profile,
            ) / 100.0

        graph_score = 0.0
        if user_id and hasattr(self.graph_service, "score_product_affinity"):
            graph_score = float(self.graph_service.score_product_affinity(user_id, product))

        rag_query = query
        if not rag_query and user_profile:
            rag_query = " ".join(user_profile.recent_keywords[:5])
        retrieval_score = self.retrieval_service.score_product_match(rag_query or "", product) if rag_query else 0.0

        lstm_score = 0.0
        if user_id and product.get("id"):
            lstm_score = self.sequence_service.score_product_for_user(
                user_id=user_id,
                candidate_product_id=str(product["id"]),
                recent_events=recent_events,
            )

        trending_score = 0.8 if product.get("is_featured") else 0.5

        return {
            "profile": round(profile_score, 4),
            "lstm": round(lstm_score, 4),
            "graph": round(graph_score, 4),
            "rag": round(retrieval_score, 4),
            "trending": round(trending_score, 4),
        }

    @staticmethod
    def _blend_component_scores(component_scores: Dict[str, float], user_id: Optional[UUID], has_query: bool) -> float:
        weights = {
            "profile": 0.20 if user_id else 0.0,
            "lstm": 0.30 if user_id else 0.0,
            "graph": 0.25 if user_id else 0.0,
            "rag": 0.20 if has_query else 0.0,
            "trending": 0.05 if user_id else 1.0,
        }
        active_total = sum(weights.values()) or 1.0
        weighted_sum = sum(component_scores[key] * weight for key, weight in weights.items())
        return round((weighted_sum / active_total) * 100.0, 2)

    def _build_reason_codes(
        self,
        product: Dict[str, Any],
        profile: Optional[UserPreferenceProfile],
        component_scores: Dict[str, float],
    ) -> List[str]:
        reasons: List[str] = []
        if profile:
            reasons.extend(
                self.scorer.get_reason_codes(
                    product_brand=product.get("brand", ""),
                    product_category=product.get("category", ""),
                    product_price=float(product.get("price", 0)),
                    user_profile=profile,
                )
            )
        if component_scores["lstm"] >= 0.2:
            reasons.append("sequence_prediction")
        if component_scores["graph"] >= 0.2:
            reasons.append("graph_similarity")
        if component_scores["rag"] >= 0.2:
            reasons.append("semantic_match")
        if component_scores["trending"] >= 0.8:
            reasons.append("featured_product")
        return list(dict.fromkeys(reasons or ["catalog_match"]))

    @staticmethod
    def _build_explanation(component_scores: Dict[str, float], reason_codes: List[str]) -> str:
        best_component = max(component_scores.items(), key=lambda item: item[1])[0]
        return f"Hybrid recommendation scored by {best_component} with signals: {', '.join(reason_codes)}."

    @staticmethod
    def _build_reason_text(reason_codes: List[str]) -> str:
        reason_map = {
            "preferred_product_group": "Vi user co xu huong mua hoac xem nhieu san pham cung nhom brand.",
            "preferred_category": "Vi user thuong tuong tac voi category nay.",
            "preferred_price_range": "Vi muc gia nay phu hop khoang gia user quan tam.",
            "sequence_prediction": "Vi chuoi hanh vi gan day cua user cho thay kha nang tiep tuc quan tam san pham nay.",
            "graph_similarity": "Vi knowledge graph tim thay quan he lien quan voi nhung item user da xem hoac mua.",
            "semantic_match": "Vi truy van hien tai co do phu hop cao voi mo ta san pham.",
            "featured_product": "Vi day la san pham noi bat trong catalog demo.",
            "catalog_match": "Vi san pham khop voi ngu canh tim kiem hien tai.",
        }
        if not reason_codes:
            return reason_map["catalog_match"]
        return " ".join(reason_map.get(code, reason_map["catalog_match"]) for code in reason_codes[:2])

    def _sync_candidate_to_graph(self, product: Dict[str, Any]) -> None:
        if hasattr(self.graph_service, "upsert_product_node"):
            try:
                self.graph_service.upsert_product_node(product)
            except Exception as exc:
                logger.debug("Skipping graph candidate sync for %s: %s", product.get("id"), exc)


class IngestKnowledgeDocumentUseCase:
    """Ingest and process knowledge document."""

    def __init__(
        self,
        doc_repo: Optional[KnowledgeDocumentRepository] = None,
        chunk_repo: Optional[KnowledgeChunkRepository] = None,
    ):
        self.doc_repo = doc_repo or DjangoKnowledgeDocumentRepository()
        self.chunk_repo = chunk_repo or DjangoKnowledgeChunkRepository()

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
            session.updated_at = timezone.now()
            self.session_repo.save(session)

        logger.debug(f"Message added to session {session_id}")
        return saved


class GenerateChatAnswerUseCase:
    """Generate answer for chat query."""

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        llm_provider = None,
        product_lookup_service: Optional[ProductCatalogLookupService] = None,
        recommendation_use_case: Optional[GenerateRecommendationsUseCase] = None,
    ):
        self.retrieval_service = retrieval_service or SimpleRetrievalService()
        self.llm_provider = llm_provider
        self.product_lookup_service = product_lookup_service or ProductCatalogLookupService()
        self.recommendation_use_case = recommendation_use_case or GenerateRecommendationsUseCase(
            retrieval_service=self.retrieval_service,
            product_lookup_service=self.product_lookup_service,
        )

    def set_llm_provider(self, provider):
        """Set LLM provider."""
        self.llm_provider = provider

    def execute(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        user_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate answer."""
        if not self.llm_provider:
            self.llm_provider = get_llm_provider()

        # Classify intent
        intent = self.llm_provider.classify_intent(query)
        entities = self.llm_provider.maybe_extract_entities(query)

        # Retrieve context
        context_chunks = self.retrieval_service.retrieve_relevant_chunks(query, limit=5)
        context = "\n".join([chunk.content for chunk in context_chunks])
        product_context = self._build_product_context(query, intent, entities, user_id=user_id)
        combined_context = "\n\n".join(part for part in [product_context, context] if part)

        # Generate answer
        answer = self.llm_provider.generate_answer(
            query=query,
            context=combined_context,
            chat_history=chat_history,
            user_context=user_context,
        )

        sources = self._build_sources(context_chunks)
        recommendation_payload = self.recommendation_use_case.recommend_from_catalog(
            user_id=user_id,
            query=query,
            limit=3,
            entities=entities,
        )
        related_products = recommendation_payload["products"]

        return {
            "answer": answer,
            "intent": intent,
            "sources": sources,
            "mode": "hybrid_rag_graph_lstm",
            "related_products": related_products,
            "confidence": round(sum(item.get("score", 0) for item in related_products) / max(len(related_products), 1) / 100.0, 4) if related_products else 0.0,
        }

    @staticmethod
    def _build_sources(context_chunks: List[KnowledgeChunk]) -> List[Dict[str, Any]]:
        """Return retrieval sources with document metadata for UI transparency."""
        if not context_chunks:
            return []

        doc_repo = DjangoKnowledgeDocumentRepository()
        documents: Dict[UUID, Optional[KnowledgeDocument]] = {}
        sources: List[Dict[str, Any]] = []

        for chunk in context_chunks:
            if chunk.document_id not in documents:
                documents[chunk.document_id] = doc_repo.get_by_id(chunk.document_id)

            document = documents.get(chunk.document_id)
            sources.append(
                {
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    "document_title": document.title if document else None,
                    "document_type": document.document_type.value if document else None,
                    "source": document.source if document else None,
                    "snippet": chunk.content[:220],
                }
            )

        return sources

    def _build_product_context(
        self,
        query: str,
        intent: str,
        entities: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> str:
        """Generate concise product context for shopping-related questions."""
        if intent != "product_search":
            return ""

        products = self.recommendation_use_case.recommend_from_catalog(
            user_id=user_id,
            query=query,
            limit=5,
            entities=entities,
        )["products"]
        if not products:
            return self._build_no_product_match_context(entities)

        lines = ["San pham phu hop hien co:"]
        for product in products:
            try:
                price_text = f"{int(float(product.get('base_price') or product.get('price', 0))):,} VND".replace(",", ".")
            except (TypeError, ValueError):
                price_text = str(product.get("base_price") or product.get("price") or "N/A")

            brand_name = product.get("brand_name") or "Khong ro nhom"
            category_name = product.get("category_name") or product.get("product_type_name") or "San pham"
            short_description = product.get("short_description") or category_name

            lines.append(
                f"- {product.get('name')}: {price_text}. Nhom product {brand_name}. Danh muc {category_name}. Mo ta ngan: {short_description}."
            )
        return "\n".join(lines)

    @staticmethod
    def _build_no_product_match_context(entities: Dict[str, Any]) -> str:
        """Return a helpful context line when catalog has no match."""
        criteria = []
        if entities.get("brands"):
            criteria.append(f"nhom product {', '.join(entities['brands'])}")
        if entities.get("categories"):
            criteria.append(f"loai {', '.join(entities['categories'])}")
        if "under_1m" in entities.get("price_filters", []):
            criteria.append("gia duoi 1 trieu")
        if "under_3m" in entities.get("price_filters", []):
            criteria.append("gia duoi 3 trieu")
        if "under_10m" in entities.get("price_filters", []):
            criteria.append("gia duoi 10 trieu")
        if "under_5m" in entities.get("price_filters", []):
            criteria.append("gia duoi 5 trieu")
        if "above_20m" in entities.get("price_filters", []):
            criteria.append("gia tren 20 trieu")

        if criteria:
            return "Khong tim thay san pham khop voi tieu chi: " + ", ".join(criteria) + "."
        return ""


def _safe_uuid(value: Any) -> Optional[UUID]:
    """Safely coerce a value to UUID."""
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


class BehaviorAnalyticsUseCase:
    """Compute behavior analytics summaries from tracked events."""

    FUNNEL_EVENT_TYPES = {
        "search_sessions": {"search"},
        "view_sessions": {"product_view", "product_click", "view_category"},
        "cart_sessions": {"add_to_cart"},
        "checkout_sessions": {"checkout_started"},
        "order_sessions": {"order_created"},
        "payment_success_sessions": {"payment_success"},
    }

    def get_summary(self) -> Dict[str, Any]:
        events = self._load_events()
        users = self._group_by_user(events)

        return {
            "total_events": len(events),
            "unique_users": len(users),
            "event_breakdown": self._event_breakdown(events),
            "top_viewed_categories": self._top_categories(events),
            "top_viewed_products": self._top_products(events),
            "conversion_funnel": self.get_funnel(events),
            "abandoned_cart_sessions": self._abandoned_cart_sessions(events),
            "co_viewed_products": self._co_occurrence(events, target_events={"product_view", "product_click"}),
            "co_purchased_products": self._co_occurrence(events, target_events={"order_created", "payment_success"}),
            "low_intent_users": self._low_intent_users(users),
            "user_segments": self._segment_users(users),
            "timeline": self._timeline(events),
        }

    def get_user_summary(self, user_id: UUID) -> Dict[str, Any]:
        events = [event for event in self._load_events() if str(event.get("user_id") or "") == str(user_id)]
        events.sort(key=lambda item: item.get("occurred_at") or timezone.now())
        recent_searches = []
        for event in reversed(events):
            keyword = (event.get("keyword") or "").strip()
            if keyword and keyword not in recent_searches:
                recent_searches.append(keyword)
        recent_searches = recent_searches[:10]

        recommendation_query = recent_searches[0] if recent_searches else ""
        next_products = GenerateRecommendationsUseCase().recommend_from_catalog(
            user_id=user_id,
            query=recommendation_query,
            limit=3,
        )["products"]

        return {
            "user_id": str(user_id),
            "total_events": len(events),
            "event_breakdown": self._event_breakdown(events),
            "dominant_categories": self._top_categories(events, limit=5),
            "recent_searches": recent_searches,
            "recent_timeline": self._timeline(events, limit=12),
            "current_intent": self._infer_user_intent(events),
            "next_likely_actions": self._predict_next_actions(events),
            "next_likely_products": next_products,
        }

    def get_funnel(self, events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, int]:
        records = events or self._load_events()
        result: Dict[str, int] = {}
        for label, event_types in self.FUNNEL_EVENT_TYPES.items():
            sessions = {
                event.get("session_id")
                for event in records
                if event.get("session_id") and event.get("event_type") in event_types
            }
            result[label] = len(sessions)
        return result

    @staticmethod
    def _load_events() -> List[Dict[str, Any]]:
        from modules.ai.infrastructure.models import BehavioralEventModel

        return list(
            BehavioralEventModel.objects.order_by("occurred_at").values(
                "id",
                "event_type",
                "user_id",
                "session_id",
                "product_id",
                "brand_name",
                "category_name",
                "price_amount",
                "keyword",
                "occurred_at",
                "metadata",
            )
        )

    @staticmethod
    def _group_by_user(events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            user_id = str(event.get("user_id") or "")
            if not user_id:
                continue
            grouped.setdefault(user_id, []).append(event)
        return grouped

    @staticmethod
    def _event_breakdown(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from collections import Counter

        counts = Counter(event.get("event_type") for event in events if event.get("event_type"))
        return [{"event_type": key, "count": value} for key, value in counts.most_common()]

    @staticmethod
    def _top_categories(events: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
        from collections import Counter

        counters = Counter(
            event.get("category_name")
            for event in events
            if event.get("category_name") and event.get("event_type") in {"product_view", "product_click", "add_to_cart", "order_created"}
        )
        return [{"category_name": key, "count": value} for key, value in counters.most_common(limit)]

    @staticmethod
    def _top_products(events: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
        from collections import Counter, defaultdict

        names = defaultdict(str)
        counters = Counter()
        for event in events:
            if event.get("event_type") not in {"product_view", "product_click"}:
                continue
            product_id = str(event.get("product_id") or "")
            if not product_id:
                continue
            counters[product_id] += 1
            metadata = event.get("metadata") or {}
            if metadata.get("product_name"):
                names[product_id] = metadata["product_name"]
        return [
            {"product_id": product_id, "product_name": names.get(product_id) or product_id, "count": count}
            for product_id, count in counters.most_common(limit)
        ]

    @staticmethod
    def _abandoned_cart_sessions(events: List[Dict[str, Any]]) -> int:
        session_summary: Dict[str, set[str]] = {}
        for event in events:
            session_id = event.get("session_id")
            event_type = event.get("event_type")
            if not session_id or not event_type:
                continue
            session_summary.setdefault(session_id, set()).add(event_type)
        return sum(
            1
            for types in session_summary.values()
            if "add_to_cart" in types and "payment_success" not in types and "order_created" not in types
        )

    @staticmethod
    def _co_occurrence(events: List[Dict[str, Any]], target_events: set[str], limit: int = 8) -> List[Dict[str, Any]]:
        from collections import Counter
        from itertools import combinations

        grouped: Dict[str, set[str]] = {}
        for event in events:
            if event.get("event_type") not in target_events:
                continue
            session_or_user = str(
                (event.get("metadata") or {}).get("order_id")
                or event.get("session_id")
                or event.get("user_id")
                or ""
            )
            product_id = str(event.get("product_id") or "")
            if not session_or_user or not product_id:
                continue
            grouped.setdefault(session_or_user, set()).add(product_id)

        pairs = Counter()
        for product_ids in grouped.values():
            if len(product_ids) < 2:
                continue
            for left, right in combinations(sorted(product_ids), 2):
                pairs[(left, right)] += 1

        return [
            {"product_a": pair[0], "product_b": pair[1], "count": count}
            for pair, count in pairs.most_common(limit)
        ]

    @staticmethod
    def _low_intent_users(grouped_events: Dict[str, List[Dict[str, Any]]]) -> int:
        low_intent_count = 0
        for events in grouped_events.values():
            event_types = {event.get("event_type") for event in events}
            if event_types and event_types.issubset({"search", "product_view", "product_click", "view_category", "chat_query"}):
                low_intent_count += 1
        return low_intent_count

    @staticmethod
    def _segment_users(grouped_events: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        counts = {
            "high_intent": 0,
            "repeat_buyers": 0,
            "chat_assisted": 0,
            "window_shoppers": 0,
            "price_sensitive": 0,
        }
        for events in grouped_events.values():
            event_types = [event.get("event_type") for event in events]
            keywords = " ".join((event.get("keyword") or "") for event in events).lower()
            if any(event_type in {"checkout_started", "order_created", "payment_success"} for event_type in event_types):
                counts["high_intent"] += 1
            if event_types.count("payment_success") >= 2:
                counts["repeat_buyers"] += 1
            if "chat_query" in event_types and any(event_type in {"add_to_cart", "order_created"} for event_type in event_types):
                counts["chat_assisted"] += 1
            if set(event_types).issubset({"search", "product_view", "product_click", "view_category", "chat_query"}):
                counts["window_shoppers"] += 1
            if any(token in keywords for token in ["duoi", "under", "gia re", "budget"]):
                counts["price_sensitive"] += 1
        return [{"segment": segment, "user_count": count} for segment, count in counts.items()]

    @staticmethod
    def _timeline(events: List[Dict[str, Any]], limit: int = 14) -> List[Dict[str, Any]]:
        from collections import Counter

        counts = Counter()
        for event in events:
            occurred_at = event.get("occurred_at")
            if not occurred_at:
                continue
            counts[occurred_at.date().isoformat()] += 1

        ordered = sorted(counts.items(), key=lambda item: item[0], reverse=True)[:limit]
        ordered.reverse()
        return [{"date": date, "event_count": count} for date, count in ordered]

    @staticmethod
    def _infer_user_intent(events: List[Dict[str, Any]]) -> str:
        if not events:
            return "new_user"
        recent_types = [event.get("event_type") for event in events[-5:]]
        if "payment_success" in recent_types:
            return "post_purchase"
        if "order_created" in recent_types or "checkout_started" in recent_types:
            return "purchase_intent"
        if "add_to_cart" in recent_types:
            return "cart_consideration"
        if "chat_query" in recent_types:
            return "guided_discovery"
        return "browsing"

    def _predict_next_actions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_events = self._load_events()
        session_sequences: Dict[str, List[str]] = {}
        for event in all_events:
            session_id = event.get("session_id")
            event_type = event.get("event_type")
            if not session_id or not event_type:
                continue
            session_sequences.setdefault(session_id, []).append(event_type)

        from collections import Counter

        transitions = Counter()
        for sequence in session_sequences.values():
            for current, nxt in zip(sequence, sequence[1:]):
                transitions[(current, nxt)] += 1

        if not events:
            return []
        last_event = events[-1].get("event_type")
        next_counts = Counter(
            nxt for (current, nxt), count in transitions.items() if current == last_event for _ in range(count)
        )
        return [{"event_type": event_type, "score": count} for event_type, count in next_counts.most_common(5)]


class CatalogSearchUseCase:
    """Search catalog via product_service with optional AI ranking."""

    def __init__(self):
        self.lookup_service = ProductCatalogLookupService()
        self.recommendations = GenerateRecommendationsUseCase()

    def execute(self, query: str, user_id: Optional[UUID] = None, limit: int = 10) -> Dict[str, Any]:
        entities = get_llm_provider().maybe_extract_entities(query) if query else {}
        return self.recommendations.recommend_from_catalog(
            user_id=user_id,
            query=query,
            limit=limit,
            entities=entities,
        )


class AiCartActionUseCase:
    """Proxy add-to-cart actions through AI service."""

    CART_BASE_URLS = [
        os.getenv("CART_SERVICE_URL", "http://cart_service:8003").rstrip("/"),
        os.getenv("CART_SERVICE_PUBLIC_URL", "http://localhost:8003").rstrip("/"),
    ]

    def execute(self, user_id: UUID, product_id: str, quantity: int = 1, variant_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {"product_id": product_id, "quantity": quantity}
        if variant_id:
            payload["variant_id"] = variant_id

        last_exception = None
        for base_url in self.CART_BASE_URLS:
            try:
                with httpx.Client(timeout=8.0, headers={"X-User-ID": str(user_id)}) as client:
                    response = client.post(f"{base_url}/api/v1/cart/items/", json=payload)
                    response.raise_for_status()
                body = response.json()
                return body.get("data", body)
            except Exception as exc:  # pragma: no cover - network fallback
                last_exception = exc
        raise RuntimeError(f"Could not add item to cart via cart_service: {last_exception}")


class AiOrderActionUseCase:
    """Proxy order creation actions through AI service."""

    ORDER_BASE_URLS = [
        os.getenv("ORDER_SERVICE_URL", "http://order_service:8004").rstrip("/"),
        os.getenv("ORDER_SERVICE_PUBLIC_URL", "http://localhost:8004").rstrip("/"),
    ]

    def execute(
        self,
        user_id: UUID,
        cart_id: str,
        shipping_address: Dict[str, Any],
        notes: str = "",
    ) -> Dict[str, Any]:
        payload = {"cart_id": cart_id, "shipping_address": shipping_address, "notes": notes}
        last_exception = None
        for base_url in self.ORDER_BASE_URLS:
            try:
                with httpx.Client(timeout=12.0, headers={"X-User-ID": str(user_id)}) as client:
                    response = client.post(f"{base_url}/api/v1/orders/from-cart/", json=payload)
                    response.raise_for_status()
                body = response.json()
                return body.get("data", body)
            except Exception as exc:  # pragma: no cover - network fallback
                last_exception = exc
        raise RuntimeError(f"Could not create order via order_service: {last_exception}")
