"""
Infrastructure domain services implementations.
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from modules.ai.domain.entities import (
    BehavioralEvent,
    UserPreferenceProfile,
    KnowledgeChunk,
)
from modules.ai.domain.value_objects import (
    PriceRange,
    EventType,
    BrandPreference,
    CategoryPreference,
    PriceRangePreference,
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
    DjangoKnowledgeChunkRepository,
)
from modules.ai.infrastructure.providers import get_ai_provider

logger = logging.getLogger(__name__)


class DefaultPriceRangeNormalizer(PriceRangeNormalizer):
    """Default price range normalization for Vietnamese market."""

    RANGES = [
        (0, 1_000_000, PriceRange.UNDER_1M),
        (1_000_000, 3_000_000, PriceRange.FROM_1M_TO_3M),
        (3_000_000, 5_000_000, PriceRange.FROM_3M_TO_5M),
        (5_000_000, 10_000_000, PriceRange.FROM_5M_TO_10M),
        (10_000_000, 20_000_000, PriceRange.FROM_10M_TO_20M),
        (20_000_000, float("inf"), PriceRange.ABOVE_20M),
    ]

    def normalize_price(self, amount: float) -> PriceRange:
        """Normalize price to range."""
        for min_val, max_val, range_enum in self.RANGES:
            if min_val <= amount < max_val:
                return range_enum
        return PriceRange.ABOVE_20M

    def get_all_ranges(self) -> List[PriceRange]:
        """Get all price ranges."""
        return [PriceRange.UNDER_1M, PriceRange.FROM_1M_TO_3M, PriceRange.FROM_3M_TO_5M,
                PriceRange.FROM_5M_TO_10M, PriceRange.FROM_10M_TO_20M, PriceRange.ABOVE_20M]


class EventBasedPreferenceProfileBuilder(PreferenceProfileBuilder):
    """Build user preference profiles from behavioral events."""

    def __init__(self, price_normalizer: Optional[PriceRangeNormalizer] = None):
        self.price_normalizer = price_normalizer or DefaultPriceRangeNormalizer()
        self.event_repo = DjangoBehavioralEventRepository()

    def build_profile_from_events(
        self,
        user_id: UUID,
        events: List[BehavioralEvent],
    ) -> UserPreferenceProfile:
        """Build profile from list of events."""
        profile = UserPreferenceProfile(id=user_id, user_id=user_id)

        for event in events:
            profile = self.update_profile_with_event(profile, event)

        return profile

    def update_profile_with_event(
        self,
        profile: UserPreferenceProfile,
        event: BehavioralEvent,
    ) -> UserPreferenceProfile:
        """Update profile based on single event."""
        if not event.has_product_context():
            return profile

        score_delta = event.get_behavior_score()

        # Update brand preference
        if event.brand_name:
            brand_prefs = list(profile.preferred_brands)
            existing = next((b for b in brand_prefs if b.brand_name == event.brand_name), None)
            if existing:
                idx = brand_prefs.index(existing)
                brand_prefs[idx] = BrandPreference(
                    brand_name=existing.brand_name,
                    score=min(100, existing.score + score_delta),
                    interaction_count=existing.interaction_count + 1,
                )
            else:
                brand_prefs.append(BrandPreference(
                    brand_name=event.brand_name,
                    score=float(min(100, score_delta)),
                    interaction_count=1,
                ))
            profile.preferred_brands = brand_prefs

        # Update category preference
        if event.category_name:
            cat_prefs = list(profile.preferred_categories)
            existing = next((c for c in cat_prefs if c.category_name == event.category_name), None)
            if existing:
                idx = cat_prefs.index(existing)
                cat_prefs[idx] = CategoryPreference(
                    category_name=existing.category_name,
                    score=min(100, existing.score + score_delta),
                    interaction_count=existing.interaction_count + 1,
                )
            else:
                cat_prefs.append(CategoryPreference(
                    category_name=event.category_name,
                    score=float(min(100, score_delta)),
                    interaction_count=1,
                ))
            profile.preferred_categories = cat_prefs

        # Update price range preference
        if event.price_amount is not None:
            price_range = self.price_normalizer.normalize_price(float(event.price_amount))
            price_prefs = list(profile.preferred_price_ranges)
            existing = next((p for p in price_prefs if p.price_range == price_range), None)
            if existing:
                idx = price_prefs.index(existing)
                price_prefs[idx] = PriceRangePreference(
                    price_range=existing.price_range,
                    score=min(100, existing.score + score_delta),
                    interaction_count=existing.interaction_count + 1,
                )
            else:
                price_prefs.append(PriceRangePreference(
                    price_range=price_range,
                    score=float(min(100, score_delta)),
                    interaction_count=1,
                ))
            profile.preferred_price_ranges = price_prefs

        # Update recent keywords
        if event.keyword:
            keywords = list(profile.recent_keywords)
            if event.keyword not in keywords:
                keywords.insert(0, event.keyword)
                if len(keywords) > 20:
                    keywords = keywords[:20]
            profile.recent_keywords = keywords

        # Update purchase intent
        if event.event_type in [EventType.ORDER_CREATED, EventType.PAYMENT_SUCCESS]:
            profile.purchase_intent_score = min(100, profile.purchase_intent_score + 10)

        # Sort preferences by score
        profile.preferred_brands = sorted(profile.preferred_brands, key=lambda x: x.score, reverse=True)
        profile.preferred_categories = sorted(profile.preferred_categories, key=lambda x: x.score, reverse=True)
        profile.preferred_price_ranges = sorted(profile.preferred_price_ranges, key=lambda x: x.score, reverse=True)

        return profile


class SimpleRecommendationScorer(RecommendationScorer):
    """Simple scoring-based recommendation engine."""

    def __init__(self, price_normalizer: Optional[PriceRangeNormalizer] = None):
        self.price_normalizer = price_normalizer or DefaultPriceRangeNormalizer()

    def score_product_for_user(
        self,
        product_id: UUID,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> float:
        """Score product for user (0-100)."""
        score = 50.0  # Base score

        # Brand match
        if user_profile.preferred_brands:
            for brand_pref in user_profile.preferred_brands[:3]:
                if product_brand.lower() == brand_pref.brand_name.lower():
                    score += 25.0 * (brand_pref.score / 100.0)
                    break

        # Category match
        if user_profile.preferred_categories:
            for cat_pref in user_profile.preferred_categories[:3]:
                if product_category.lower() == cat_pref.category_name.lower():
                    score += 15.0 * (cat_pref.score / 100.0)
                    break

        # Price match
        product_price_range = self.price_normalizer.normalize_price(product_price)
        if user_profile.preferred_price_ranges:
            for price_pref in user_profile.preferred_price_ranges[:3]:
                if product_price_range == price_pref.price_range:
                    score += 10.0 * (price_pref.score / 100.0)
                    break

        return min(100, max(0, score))

    def get_reason_codes(
        self,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> List[str]:
        """Get reason codes."""
        reasons = []

        if user_profile.preferred_brands:
            for brand_pref in user_profile.preferred_brands[:3]:
                if product_brand.lower() == brand_pref.brand_name.lower():
                    reasons.append("preferred_brand")
                    break

        if user_profile.preferred_categories:
            for cat_pref in user_profile.preferred_categories[:3]:
                if product_category.lower() == cat_pref.category_name.lower():
                    reasons.append("preferred_category")
                    break

        product_price_range = self.price_normalizer.normalize_price(product_price)
        if user_profile.preferred_price_ranges:
            for price_pref in user_profile.preferred_price_ranges[:3]:
                if product_price_range == price_pref.price_range:
                    reasons.append("preferred_price_range")
                    break

        if not reasons:
            reasons.append("trending")

        return reasons


class MockGraphService(GraphService):
    """Mock graph service (Neo4j integration placeholder)."""

    def sync_event_to_graph(self, event: BehavioralEvent) -> None:
        """
        In real implementation, would sync to Neo4j.
        For now, just log.
        """
        if event.user_id and event.has_product_context():
            logger.debug(
                f"Mock: Syncing {event.event_type} to graph for user {event.user_id}"
            )

    def get_user_top_brands(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top brands from graph."""
        # Mock implementation - returns empty
        return []

    def get_user_top_categories(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top categories from graph."""
        # Mock implementation - returns empty
        return []

    def get_related_products(
        self,
        product_id: UUID,
        limit: int = 5,
    ) -> List[UUID]:
        """Get related products."""
        # Mock implementation - returns empty
        return []


class SemanticRetrievalService(RetrievalService):
    """Semantic retrieval over pgvector-backed knowledge chunks."""

    def __init__(self):
        self.chunk_repo = DjangoKnowledgeChunkRepository()
        self.provider = get_ai_provider()

    def retrieve_relevant_chunks(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeChunk]:
        """Use a query embedding so retrieval remains grounded in stored vectors."""
        query_embedding = self.provider.generate_embeddings([query])[0]
        return self.chunk_repo.search_similar(
            query,
            limit=limit,
            filters=filters,
            query_embedding=query_embedding,
        )

    def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        limit: int = 5,
    ) -> List[KnowledgeChunk]:
        """Restrict semantic retrieval to a single knowledge type."""
        return self.retrieve_relevant_chunks(
            query,
            limit=limit,
            filters={"document_types": [document_type]},
        )
