"""Application DTOs for catalog use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class CategoryUpsertDTO:
    """Validated category payload for create/update operations."""

    name: str
    slug: str
    description: str = ""
    image_url: str = ""
    status: str = "active"
    sort_order: int = 0
    parent_id: Optional[str] = None


@dataclass(frozen=True)
class ProductUpsertDTO:
    """Validated product payload for create/update operations."""

    name: str
    slug: str
    category_id: str
    product_type_id: str
    base_price: Decimal
    currency: str = "VND"
    short_description: str = ""
    description: str = ""
    brand_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "draft"
    is_active: bool = True
    is_featured: bool = False
    thumbnail_url: str = ""
    seo_title: str = ""
    seo_description: str = ""


@dataclass(frozen=True)
class ProductQueryDTO:
    """Filters supported by public/admin product listing APIs."""

    category_id: Optional[str] = None
    category_slug: Optional[str] = None
    brand_id: Optional[str] = None
    product_type_id: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    search: str = ""

