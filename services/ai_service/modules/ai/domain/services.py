"""
Domain services.
Interfaces for domain-level business logic.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from modules.ai.domain.entities import (
    BehavioralEvent,
    UserPreferenceProfile,
    KnowledgeChunk,
)
from modules.ai.domain.value_objects import PriceRange


class PriceRangeNormalizer(ABC):
    """Service to normalize prices to ranges."""

    @abstractmethod
    def normalize_price(self, amount: float) -> PriceRange:
        """Normalize a price amount to a price range."""
        pass

    @abstractmethod
    def get_all_ranges(self) -> List[PriceRange]:
        """Get all available price ranges."""
        pass


class PreferenceProfileBuilder(ABC):
    """Service to build user preference profiles from events."""

    @abstractmethod
    def build_profile_from_events(
        self,
        user_id: UUID,
        events: List[BehavioralEvent],
    ) -> UserPreferenceProfile:
        """Build a profile from a list of events."""
        pass

    @abstractmethod
    def update_profile_with_event(
        self,
        profile: UserPreferenceProfile,
        event: BehavioralEvent,
    ) -> UserPreferenceProfile:
        """Update profile based on a single new event."""
        pass


class RecommendationScorer(ABC):
    """Service for scoring recommendations."""

    @abstractmethod
    def score_product_for_user(
        self,
        product_id: UUID,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> float:
        """Score a product for recommendation to a user."""
        pass

    @abstractmethod
    def get_reason_codes(
        self,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> List[str]:
        """Get reason codes for why product was recommended."""
        pass


class GraphService(ABC):
    """Service for graph operations."""

    @abstractmethod
    def sync_event_to_graph(self, event: BehavioralEvent) -> None:
        """Sync a behavioral event to the graph (Neo4j)."""
        pass

    @abstractmethod
    def get_user_top_brands(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        """Get user's top brands from graph."""
        pass

    @abstractmethod
    def get_user_top_categories(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        """Get user's top categories from graph."""
        pass

    @abstractmethod
    def get_related_products(
        self,
        product_id: UUID,
        limit: int = 5,
    ) -> List[UUID]:
        """Get products related to given product."""
        pass


class RetrievalService(ABC):
    """Service for knowledge retrieval (RAG)."""

    @abstractmethod
    def retrieve_relevant_chunks(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeChunk]:
        """Retrieve relevant knowledge chunks for a query."""
        pass

    @abstractmethod
    def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        limit: int = 5,
    ) -> List[KnowledgeChunk]:
        """Retrieve chunks by specific document type."""
        pass
