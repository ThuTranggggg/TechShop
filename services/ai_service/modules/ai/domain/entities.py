"""
Domain entities for AI service.
Core business concepts.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from modules.ai.domain.value_objects import (
    EventType,
    PriceRange,
    BrandPreference,
    CategoryPreference,
    PriceRangePreference,
    DocumentType,
    ChatRole,
)


@dataclass
class BehavioralEvent:
    """
    Domain entity for behavioral events.
    Core data for AI service tracking.
    """
    id: UUID
    event_type: EventType
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    price_amount: Optional[float] = None
    price_range: Optional[PriceRange] = None
    keyword: Optional[str] = None
    source_service: Optional[str] = None
    occurred_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def get_behavior_score(self) -> float:
        """
        Score business logic for different event types.
        Used for preference calculations.
        """
        scores = {
            EventType.PRODUCT_VIEW: 1,
            EventType.PRODUCT_CLICK: 1,
            EventType.SEARCH: 2,
            EventType.ADD_TO_CART: 3,
            EventType.CHECKOUT_STARTED: 4,
            EventType.ORDER_CREATED: 5,
            EventType.PAYMENT_SUCCESS: 6,
            EventType.CHAT_QUERY: 2,
        }
        return scores.get(self.event_type, 0)

    def has_product_context(self) -> bool:
        """Check if event has product-related context."""
        return bool(self.product_id or self.brand_name or self.category_name)

    def has_price_context(self) -> bool:
        """Check if event has price context."""
        return self.price_amount is not None


@dataclass
class UserPreferenceProfile:
    """
    Domain entity for user preference profile.
    Derived from behavioral events.
    """
    id: UUID
    user_id: UUID
    preferred_brands: List[BrandPreference] = field(default_factory=list)
    preferred_categories: List[CategoryPreference] = field(default_factory=list)
    preferred_price_ranges: List[PriceRangePreference] = field(default_factory=list)
    recent_keywords: List[str] = field(default_factory=list)
    preference_score_summary: Dict[str, float] = field(default_factory=dict)
    purchase_intent_score: float = 0.0
    last_interaction_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_top_brand(self, limit: int = 1) -> List[BrandPreference]:
        """Get top preferred brands."""
        return sorted(self.preferred_brands, key=lambda x: x.score, reverse=True)[:limit]

    def get_top_category(self, limit: int = 1) -> List[CategoryPreference]:
        """Get top preferred categories."""
        return sorted(self.preferred_categories, key=lambda x: x.score, reverse=True)[:limit]

    def get_top_price_range(self, limit: int = 1) -> List[PriceRangePreference]:
        """Get top preferred price ranges."""
        return sorted(self.preferred_price_ranges, key=lambda x: x.score, reverse=True)[:limit]

    def is_high_intent_user(self, threshold: float = 50.0) -> bool:
        """Check if user has high purchase intent."""
        return self.purchase_intent_score >= threshold


@dataclass
class KnowledgeDocument:
    """
    Domain entity for knowledge documents.
    Used for RAG chat.
    """
    id: UUID
    document_type: DocumentType
    title: str
    slug: Optional[str] = None
    source: str = "internal"
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def should_be_indexed(self) -> bool:
        """Check if document should be indexed."""
        return self.is_active and bool(self.content)


@dataclass
class KnowledgeChunk:
    """
    Domain entity for knowledge chunks.
    For retrieval-augmented generation.
    """
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    embedding_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Check if chunk is valid."""
        return bool(self.content.strip()) and self.chunk_index >= 0


@dataclass
class ChatSession:
    """
    Domain entity for chat sessions.
    Groups related chat messages.
    """
    id: UUID
    user_id: Optional[UUID] = None
    session_title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def should_be_archived(self) -> bool:
        """Simple heuristic: archive if not updated in long time."""
        if not self.updated_at:
            return False
        from datetime import timedelta
        return (datetime.now() - self.updated_at) > timedelta(days=30)


@dataclass
class ChatMessage:
    """
    Domain entity for chat messages.
    Individual messages in a session.
    """
    id: UUID
    session_id: UUID
    role: ChatRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == ChatRole.USER

    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == ChatRole.ASSISTANT
