"""
Value objects for AI domain.
Immutable objects that define domain concepts.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from decimal import Decimal


class EventType(str, Enum):
    """Types of behavioral events."""
    SEARCH = "search"
    PRODUCT_VIEW = "product_view"
    PRODUCT_CLICK = "product_click"
    VIEW_CATEGORY = "view_category"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    ADD_TO_WISHLIST = "add_to_wishlist"
    CHECKOUT_STARTED = "checkout_started"
    ORDER_CREATED = "order_created"
    ORDER_CANCEL = "order_cancel"
    PAYMENT_SUCCESS = "payment_success"
    CHAT_QUERY = "chat_query"


class PriceRange(str, Enum):
    """Normalized price ranges for Vietnamese market."""
    UNDER_1M = "under_1m"
    FROM_1M_TO_3M = "from_1m_to_3m"
    FROM_3M_TO_5M = "from_3m_to_5m"
    FROM_5M_TO_10M = "from_5m_to_10m"
    FROM_10M_TO_20M = "from_10m_to_20m"
    ABOVE_20M = "above_20m"


@dataclass(frozen=True)
class Money:
    """Value object for monetary amount."""
    amount: Decimal
    currency: str = "VND"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")


@dataclass(frozen=True)
class BrandPreference:
    """Value object for brand preference."""
    brand_name: str
    score: float
    interaction_count: int

    def __post_init__(self):
        if self.score < 0 or self.score > 100:
            raise ValueError("Score must be between 0 and 100")
        if self.interaction_count < 0:
            raise ValueError("Interaction count cannot be negative")


@dataclass(frozen=True)
class CategoryPreference:
    """Value object for category preference."""
    category_name: str
    score: float
    interaction_count: int

    def __post_init__(self):
        if self.score < 0 or self.score > 100:
            raise ValueError("Score must be between 0 and 100")
        if self.interaction_count < 0:
            raise ValueError("Interaction count cannot be negative")


@dataclass(frozen=True)
class PriceRangePreference:
    """Value object for price range preference."""
    price_range: PriceRange
    score: float
    interaction_count: int

    def __post_init__(self):
        if self.score < 0 or self.score > 100:
            raise ValueError("Score must be between 0 and 100")
        if self.interaction_count < 0:
            raise ValueError("Interaction count cannot be negative")


class DocumentType(str, Enum):
    """Types of knowledge documents."""
    FAQ = "faq"
    RETURN_POLICY = "return_policy"
    PAYMENT_POLICY = "payment_policy"
    SHIPPING_POLICY = "shipping_policy"
    PRODUCT_GUIDE = "product_guide"
    SUPPORT_ARTICLE = "support_article"
    PRODUCT_CATALOG = "product_catalog"


class ChatRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatIntent(str, Enum):
    """Intent classification for chat queries."""
    PRODUCT_SEARCH = "product_search"
    PRODUCT_EXPLORATION = "product_exploration"
    POLICY_QUESTION = "policy_question"
    ORDER_STATUS = "order_status"
    SHIPMENT_STATUS = "shipment_status"
    PAYMENT_STATUS = "payment_status"
    GENERAL_SUPPORT = "general_support"
    UNKNOWN = "unknown"
