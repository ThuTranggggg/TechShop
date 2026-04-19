"""Repository layer for catalog data access."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from django.db.models import Count, Prefetch, Q, QuerySet

from ..application.dtos import ProductQueryDTO
from ..domain.enums import CategoryStatus, ProductStatus
from .models import CategoryModel, ProductModel, ProductVariantModel, ProductMediaModel


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


class CategoryRepository:
    """Category persistence and query helper methods."""

    def get_queryset(self, include_inactive: bool = False) -> QuerySet[CategoryModel]:
        queryset = CategoryModel.objects.annotate(
            children_count=Count("children", distinct=True),
            products_count=Count(
                "products",
                filter=Q(
                    products__status=ProductStatus.ACTIVE.value,
                    products__is_active=True,
                ),
                distinct=True,
            ),
        ).select_related("parent")

        if not include_inactive:
            queryset = queryset.filter(status=CategoryStatus.ACTIVE.value, is_active=True)
        return queryset.order_by("sort_order", "name")

    def get_by_lookup(self, lookup: str, include_inactive: bool = False) -> CategoryModel:
        queryset = self.get_queryset(include_inactive=include_inactive)
        if _is_uuid(lookup):
            return queryset.get(id=lookup)
        return queryset.get(slug=lookup)

    def create(self, **payload) -> CategoryModel:
        return CategoryModel.objects.create(**payload)

    def save(self, instance: CategoryModel, update_fields: Optional[list[str]] = None) -> CategoryModel:
        if update_fields:
            instance.save(update_fields=update_fields)
        else:
            instance.save()
        return instance


class ProductRepository:
    """Product persistence and query helper methods."""

    def get_public_queryset(self) -> QuerySet[ProductModel]:
        return (
            ProductModel.objects.filter(
                status=ProductStatus.ACTIVE.value,
                is_active=True,
                published_at__isnull=False,
                category__status=CategoryStatus.ACTIVE.value,
                category__is_active=True,
            )
            .select_related("category", "brand", "product_type")
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariantModel.objects.filter(is_active=True).order_by("-is_default", "name")),
                Prefetch("media", queryset=ProductMediaModel.objects.order_by("sort_order", "-is_primary")),
            )
        )

    def get_admin_queryset(self) -> QuerySet[ProductModel]:
        return (
            ProductModel.objects.select_related("category", "brand", "product_type")
            .prefetch_related(
                Prefetch("variants", queryset=ProductVariantModel.objects.order_by("-is_default", "name")),
                Prefetch("media", queryset=ProductMediaModel.objects.order_by("sort_order", "-is_primary")),
            )
        )

    def apply_filters(self, queryset: QuerySet[ProductModel], filters: ProductQueryDTO) -> QuerySet[ProductModel]:
        if filters.category_id:
            queryset = queryset.filter(category_id=filters.category_id)
        if filters.category_slug:
            queryset = queryset.filter(category__slug=filters.category_slug)
        if filters.brand_id:
            queryset = queryset.filter(brand_id=filters.brand_id)
        if filters.product_type_id:
            queryset = queryset.filter(product_type_id=filters.product_type_id)
        if filters.status:
            queryset = queryset.filter(status=filters.status)
        if filters.is_active is not None:
            queryset = queryset.filter(is_active=filters.is_active)
        if filters.is_featured is not None:
            queryset = queryset.filter(is_featured=filters.is_featured)
        if filters.min_price is not None:
            queryset = queryset.filter(base_price__gte=filters.min_price)
        if filters.max_price is not None:
            queryset = queryset.filter(base_price__lte=filters.max_price)
        if filters.search:
            queryset = queryset.filter(
                Q(name__icontains=filters.search)
                | Q(slug__icontains=filters.search)
                | Q(short_description__icontains=filters.search)
                | Q(description__icontains=filters.search)
                | Q(category__name__icontains=filters.search)
                | Q(category__slug__icontains=filters.search)
                | Q(brand__name__icontains=filters.search)
            )
        return queryset

    def get_by_lookup(self, lookup: str, public_only: bool = True) -> ProductModel:
        queryset = self.get_public_queryset() if public_only else self.get_admin_queryset()
        if _is_uuid(lookup):
            return queryset.get(id=lookup)
        return queryset.get(slug=lookup)

    def create(self, **payload) -> ProductModel:
        return ProductModel.objects.create(**payload)

    def save(self, instance: ProductModel, update_fields: Optional[list[str]] = None) -> ProductModel:
        if update_fields:
            instance.save(update_fields=update_fields)
        else:
            instance.save()
        return instance

