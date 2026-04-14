"""
Domain entities for Catalog context.

Business logic for Product, Category, Brand, etc.
These are pure domain models without Django ORM dependencies.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import uuid

from .enums import ProductStatus, Currency


@dataclass
class Slug:
    """Value object for URL-safe slug."""
    value: str

    def __post_init__(self):
        """Validate slug format."""
        if not self.value or len(self.value) < 1:
            raise ValueError("Slug cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in self.value):
            raise ValueError("Slug must contain only alphanumeric, dash, or underscore")

    def __str__(self):
        return self.value


@dataclass
class Money:
    """Value object for price with currency."""
    amount: float
    currency: Currency

    def __post_init__(self):
        """Validate money."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not isinstance(self.currency, Currency):
            raise ValueError("Currency must be a Currency enum")

    def __str__(self):
        return f"{self.amount} {self.currency.value}"


@dataclass
class SKU:
    """Value object for Product SKU."""
    value: str

    def __post_init__(self):
        """Validate SKU."""
        if not self.value or len(self.value) < 1:
            raise ValueError("SKU cannot be empty")

    def __str__(self):
        return self.value


class Category:
    """Category entity with business logic."""

    def __init__(
        self,
        id: uuid.UUID,
        name: str,
        slug: Slug,
        parent_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        is_active: bool = True,
        sort_order: int = 0,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.slug = slug
        self.parent_id = parent_id
        self.description = description
        self.image_url = image_url
        self.is_active = is_active
        self.sort_order = sort_order
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def can_set_parent(self, potential_parent_id: Optional[uuid.UUID], all_categories: List["Category"]) -> bool:
        """Check if setting parent would create circular reference."""
        if potential_parent_id is None:
            return True

        current = potential_parent_id
        visited = set()

        while current is not None:
            if current == self.id:
                return False  # Circular reference detected
            if current in visited:
                return False  # Infinite loop detected
            visited.add(current)

            # Find parent of current
            current_cat = next((c for c in all_categories if c.id == current), None)
            current = current_cat.parent_id if current_cat else None

        return True


class Brand:
    """Brand entity."""

    def __init__(
        self,
        id: uuid.UUID,
        name: str,
        slug: Slug,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.slug = slug
        self.description = description
        self.logo_url = logo_url
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class ProductType:
    """ProductType entity."""

    def __init__(
        self,
        id: uuid.UUID,
        code: str,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.code = code
        self.name = name
        self.description = description
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class Product:
    """Product entity - main aggregate root."""

    def __init__(
        self,
        id: uuid.UUID,
        name: str,
        slug: Slug,
        short_description: Optional[str],
        description: Optional[str],
        category_id: uuid.UUID,
        brand_id: Optional[uuid.UUID],
        product_type_id: uuid.UUID,
        base_price: Money,
        attributes: Dict[str, Any] = None,
        status: ProductStatus = ProductStatus.DRAFT,
        is_active: bool = True,
        is_featured: bool = False,
        thumbnail_url: Optional[str] = None,
        seo_title: Optional[str] = None,
        seo_description: Optional[str] = None,
        published_at: Optional[datetime] = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.slug = slug
        self.short_description = short_description
        self.description = description
        self.category_id = category_id
        self.brand_id = brand_id
        self.product_type_id = product_type_id
        self.base_price = base_price
        self.attributes = attributes or {}
        self.status = status
        self.is_active = is_active
        self.is_featured = is_featured
        self.thumbnail_url = thumbnail_url
        self.seo_title = seo_title
        self.seo_description = seo_description
        self.published_at = published_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def publish(self) -> None:
        """Publish product."""
        if self.status == ProductStatus.DRAFT:
            self.status = ProductStatus.ACTIVE
            self.published_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    def unpublish(self) -> None:
        """Unpublish product."""
        if self.status == ProductStatus.ACTIVE:
            self.status = ProductStatus.DRAFT
            self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate product."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate product."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def is_published(self) -> bool:
        """Check if product is published and visible to public."""
        return (
            self.status == ProductStatus.ACTIVE
            and self.is_active
            and self.published_at is not None
        )


class ProductVariant:
    """Product variant entity."""

    def __init__(
        self,
        id: uuid.UUID,
        product_id: uuid.UUID,
        sku: SKU,
        name: str,
        attributes: Dict[str, Any] = None,
        price_override: Optional[Money] = None,
        compare_at_price: Optional[Money] = None,
        barcode: Optional[str] = None,
        weight: Optional[float] = None,
        is_default: bool = False,
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.product_id = product_id
        self.sku = sku
        self.name = name
        self.attributes = attributes or {}
        self.price_override = price_override
        self.compare_at_price = compare_at_price
        self.barcode = barcode
        self.weight = weight
        self.is_default = is_default
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def get_effective_price(self, product_base_price: Money) -> Money:
        """Get effective price: variant override or product base price."""
        return self.price_override or product_base_price


class ProductMedia:
    """Product media/image entity."""

    def __init__(
        self,
        id: uuid.UUID,
        product_id: Optional[uuid.UUID],
        variant_id: Optional[uuid.UUID],
        media_url: str,
        alt_text: Optional[str] = None,
        sort_order: int = 0,
        is_primary: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.product_id = product_id
        self.variant_id = variant_id
        self.media_url = media_url
        self.alt_text = alt_text
        self.sort_order = sort_order
        self.is_primary = is_primary
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
