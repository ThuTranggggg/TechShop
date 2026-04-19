"""Application services for catalog use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..application.dtos import CategoryUpsertDTO, ProductQueryDTO, ProductUpsertDTO
from ..domain.enums import CategoryStatus, ProductStatus
from ..infrastructure.models import (
    BrandModel,
    CategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductTypeModel,
    ProductVariantModel,
)
from ..infrastructure.repositories import CategoryRepository, ProductRepository


class CategoryQueryService:
    """Read-only category queries."""

    def __init__(self, repository: Optional[CategoryRepository] = None):
        self.repository = repository or CategoryRepository()

    def list_categories(self, include_inactive: bool = False) -> QuerySet[CategoryModel]:
        return self.repository.get_queryset(include_inactive=include_inactive)

    def get_category(self, lookup: str, include_inactive: bool = False) -> CategoryModel:
        try:
            return self.repository.get_by_lookup(lookup, include_inactive=include_inactive)
        except CategoryModel.DoesNotExist as exc:
            raise ValidationError("Category not found") from exc


class CategoryCommandService:
    """Write operations for categories."""

    def __init__(self, repository: Optional[CategoryRepository] = None):
        self.repository = repository or CategoryRepository()

    @transaction.atomic
    def create_category(self, payload: CategoryUpsertDTO) -> CategoryModel:
        parent = self._resolve_parent(payload.parent_id)
        self._validate_unique_slug(payload.slug)
        category = CategoryModel(
            name=payload.name,
            slug=payload.slug,
            parent=parent,
            description=payload.description,
            image_url=payload.image_url,
            status=payload.status,
            is_active=payload.status == CategoryStatus.ACTIVE.value,
            sort_order=payload.sort_order,
        )
        category.full_clean()
        return self.repository.save(category)

    @transaction.atomic
    def update_category(self, lookup: str, payload: CategoryUpsertDTO) -> CategoryModel:
        category = self.repository.get_by_lookup(lookup, include_inactive=True)
        parent = self._resolve_parent(payload.parent_id)
        self._validate_unique_slug(payload.slug, exclude_id=category.id)

        category.name = payload.name
        category.slug = payload.slug
        category.parent = parent
        category.description = payload.description
        category.image_url = payload.image_url
        category.status = payload.status
        category.is_active = payload.status == CategoryStatus.ACTIVE.value
        category.sort_order = payload.sort_order
        category.full_clean()
        return self.repository.save(category)

    @transaction.atomic
    def delete_category(self, lookup: str) -> None:
        category = self.repository.get_by_lookup(lookup, include_inactive=True)
        if category.products.exists():
            raise ValidationError("Cannot delete category while products still belong to it")
        category.delete()

    def _resolve_parent(self, parent_id: Optional[str]) -> Optional[CategoryModel]:
        if not parent_id:
            return None
        try:
            return CategoryModel.objects.get(id=parent_id)
        except CategoryModel.DoesNotExist as exc:
            raise ValidationError("Parent category does not exist") from exc

    @staticmethod
    def _validate_unique_slug(slug: str, exclude_id: Optional[uuid.UUID] = None) -> None:
        queryset = CategoryModel.objects.filter(slug=slug)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        if queryset.exists():
            raise ValidationError(f"Category with slug '{slug}' already exists")


class BrandService:
    """Service for brand operations."""

    @staticmethod
    def create_brand(
        name: str,
        slug: str,
        description: str = "",
        logo_url: str = "",
        is_active: bool = True,
    ) -> BrandModel:
        if BrandModel.objects.filter(slug=slug).exists():
            raise ValidationError(f"Brand with slug '{slug}' already exists")

        brand = BrandModel.objects.create(
            name=name,
            slug=slug,
            description=description,
            logo_url=logo_url,
            is_active=is_active,
        )
        return brand

    @staticmethod
    def update_brand(brand_id: uuid.UUID, **kwargs) -> BrandModel:
        brand = BrandModel.objects.get(id=brand_id)

        if "slug" in kwargs and kwargs["slug"] != brand.slug:
            if BrandModel.objects.filter(slug=kwargs["slug"]).exists():
                raise ValidationError(f"Slug '{kwargs['slug']}' already exists")

        for field, value in kwargs.items():
            setattr(brand, field, value)

        brand.save()
        return brand


class ProductTypeService:
    """Service for product type operations."""

    @staticmethod
    def create_product_type(
        code: str,
        name: str,
        description: str = "",
        is_active: bool = True,
    ) -> ProductTypeModel:
        if ProductTypeModel.objects.filter(code=code).exists():
            raise ValidationError(f"Product type with code '{code}' already exists")

        product_type = ProductTypeModel.objects.create(
            code=code,
            name=name,
            description=description,
            is_active=is_active,
        )
        return product_type

    @staticmethod
    def update_product_type(product_type_id: uuid.UUID, **kwargs) -> ProductTypeModel:
        product_type = ProductTypeModel.objects.get(id=product_type_id)

        if "code" in kwargs and kwargs["code"] != product_type.code:
            if ProductTypeModel.objects.filter(code=kwargs["code"]).exists():
                raise ValidationError(f"Code '{kwargs['code']}' already exists")

        for field, value in kwargs.items():
            setattr(product_type, field, value)

        product_type.save()
        return product_type


class ProductQueryService:
    """Read-only product queries."""

    def __init__(self, repository: Optional[ProductRepository] = None):
        self.repository = repository or ProductRepository()

    def list_public_products(self, filters: Optional[ProductQueryDTO] = None) -> QuerySet[ProductModel]:
        queryset = self.repository.get_public_queryset()
        return self.repository.apply_filters(queryset, filters or ProductQueryDTO())

    def list_admin_products(self, filters: Optional[ProductQueryDTO] = None) -> QuerySet[ProductModel]:
        queryset = self.repository.get_admin_queryset()
        return self.repository.apply_filters(queryset, filters or ProductQueryDTO())

    def get_product(self, lookup: str, public_only: bool = True) -> ProductModel:
        try:
            return self.repository.get_by_lookup(lookup, public_only=public_only)
        except ProductModel.DoesNotExist as exc:
            raise ValidationError("Product not found") from exc

    def list_products_for_category(self, category_lookup: str, public_only: bool = True) -> QuerySet[ProductModel]:
        category = CategoryRepository().get_by_lookup(category_lookup, include_inactive=not public_only)
        filters = ProductQueryDTO(category_id=str(category.id))
        if public_only:
            return self.list_public_products(filters)
        return self.list_admin_products(filters)


class ProductCommandService:
    """Write operations for products."""

    def __init__(self, repository: Optional[ProductRepository] = None):
        self.repository = repository or ProductRepository()

    @transaction.atomic
    def create_product(self, payload: ProductUpsertDTO) -> ProductModel:
        self._validate_unique_slug(payload.slug)
        category = self._resolve_category(payload.category_id)
        product_type = self._resolve_product_type(payload.product_type_id)
        brand = self._resolve_brand(payload.brand_id)

        product = ProductModel(
            name=payload.name,
            slug=payload.slug,
            short_description=payload.short_description,
            description=payload.description,
            category=category,
            brand=brand,
            product_type=product_type,
            base_price=payload.base_price,
            currency=payload.currency,
            attributes=payload.attributes,
            status=payload.status,
            is_active=payload.is_active,
            is_featured=payload.is_featured,
            thumbnail_url=payload.thumbnail_url,
            seo_title=payload.seo_title,
            seo_description=payload.seo_description,
            published_at=timezone.now() if payload.status == ProductStatus.ACTIVE.value else None,
        )
        product.full_clean()
        return self.repository.save(product)

    @transaction.atomic
    def update_product(self, lookup: str, payload: ProductUpsertDTO) -> ProductModel:
        product = self.repository.get_by_lookup(lookup, public_only=False)
        self._validate_unique_slug(payload.slug, exclude_id=product.id)

        product.name = payload.name
        product.slug = payload.slug
        product.category = self._resolve_category(payload.category_id)
        product.product_type = self._resolve_product_type(payload.product_type_id)
        product.brand = self._resolve_brand(payload.brand_id)
        product.short_description = payload.short_description
        product.description = payload.description
        product.base_price = payload.base_price
        product.currency = payload.currency
        product.attributes = payload.attributes
        product.status = payload.status
        product.is_active = payload.is_active
        product.is_featured = payload.is_featured
        product.thumbnail_url = payload.thumbnail_url
        product.seo_title = payload.seo_title
        product.seo_description = payload.seo_description
        if payload.status == ProductStatus.ACTIVE.value and product.published_at is None:
            product.published_at = timezone.now()
        if payload.status != ProductStatus.ACTIVE.value:
            product.published_at = None
        product.full_clean()
        return self.repository.save(product)

    @staticmethod
    @transaction.atomic
    def publish_product(product_id: uuid.UUID) -> ProductModel:
        product = ProductModel.objects.select_for_update().get(id=product_id)

        if product.status != ProductStatus.DRAFT.value:
            raise ValidationError("Only draft products can be published")

        product.status = ProductStatus.ACTIVE.value
        product.published_at = timezone.now()
        product.save(update_fields=["status", "published_at", "updated_at"])
        return product

    @staticmethod
    @transaction.atomic
    def unpublish_product(product_id: uuid.UUID) -> ProductModel:
        product = ProductModel.objects.select_for_update().get(id=product_id)

        if product.status != ProductStatus.ACTIVE.value:
            raise ValidationError("Only active products can be unpublished")

        product.status = ProductStatus.DRAFT.value
        product.published_at = None
        product.save(update_fields=["status", "published_at", "updated_at"])
        return product

    @staticmethod
    def activate_product(product_id: uuid.UUID) -> ProductModel:
        product = ProductModel.objects.get(id=product_id)
        product.is_active = True
        product.save(update_fields=["is_active", "updated_at"])
        return product

    @staticmethod
    def deactivate_product(product_id: uuid.UUID) -> ProductModel:
        product = ProductModel.objects.get(id=product_id)
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return product

    @staticmethod
    def get_product_snapshot(product_id: uuid.UUID) -> Dict[str, Any]:
        try:
            product = (
                ProductModel.objects.select_related("category", "brand", "product_type")
                .prefetch_related("variants", "media")
                .get(id=product_id)
            )
        except ProductModel.DoesNotExist as exc:
            raise ValidationError("Product not found") from exc

        default_variant = product.default_variant

        return {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "category_id": str(product.category.id),
            "category_name": product.category.name,
            "category_slug": product.category.slug,
            "brand_id": str(product.brand.id) if product.brand else None,
            "brand_name": product.brand.name if product.brand else None,
            "product_type": product.product_type.code,
            "base_price": float(product.base_price),
            "currency": product.currency,
            "thumbnail_url": product.thumbnail_url,
            "status": product.status,
            "is_active": product.is_active,
            "is_featured": product.is_featured,
            "attributes": product.attributes,
            "default_variant": {
                "id": str(default_variant.id),
                "sku": default_variant.sku,
                "name": default_variant.name,
                "effective_price": float(default_variant.get_effective_price()),
                "attributes": default_variant.attributes,
            } if default_variant else None,
        }

    @staticmethod
    def _validate_unique_slug(slug: str, exclude_id: Optional[uuid.UUID] = None) -> None:
        queryset = ProductModel.objects.filter(slug=slug)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        if queryset.exists():
            raise ValidationError(f"Product with slug '{slug}' already exists")

    @staticmethod
    def _resolve_category(category_id: str) -> CategoryModel:
        try:
            category = CategoryModel.objects.get(id=category_id)
        except CategoryModel.DoesNotExist as exc:
            raise ValidationError("Category does not exist") from exc
        if category.status != CategoryStatus.ACTIVE.value:
            raise ValidationError("Products can only be assigned to active categories")
        return category

    @staticmethod
    def _resolve_product_type(product_type_id: str) -> ProductTypeModel:
        try:
            return ProductTypeModel.objects.get(id=product_type_id)
        except ProductTypeModel.DoesNotExist as exc:
            raise ValidationError("Product type does not exist") from exc

    @staticmethod
    def _resolve_brand(brand_id: Optional[str]) -> Optional[BrandModel]:
        if not brand_id:
            return None
        try:
            return BrandModel.objects.get(id=brand_id)
        except BrandModel.DoesNotExist as exc:
            raise ValidationError("Brand does not exist") from exc


class ProductVariantService:
    """Service for product variant operations."""

    @staticmethod
    @transaction.atomic
    def create_variant(
        product_id: uuid.UUID,
        sku: str,
        name: str,
        attributes: Dict[str, Any] = None,
        price_override: Optional[float] = None,
        compare_at_price: Optional[float] = None,
        barcode: str = "",
        weight: Optional[float] = None,
        is_default: bool = False,
        is_active: bool = True,
    ) -> ProductVariantModel:
        product = ProductModel.objects.get(id=product_id)

        if ProductVariantModel.objects.filter(sku=sku).exists():
            raise ValidationError(f"SKU '{sku}' already exists")

        if is_default and ProductVariantModel.objects.filter(product=product, is_default=True).exists():
            raise ValidationError("Product already has a default variant")

        variant = ProductVariantModel.objects.create(
            product=product,
            sku=sku,
            name=name,
            attributes=attributes or {},
            price_override=price_override,
            compare_at_price=compare_at_price,
            barcode=barcode,
            weight=weight,
            is_default=is_default,
            is_active=is_active,
        )
        return variant

    @staticmethod
    @transaction.atomic
    def set_default_variant(variant_id: uuid.UUID) -> ProductVariantModel:
        variant = ProductVariantModel.objects.select_for_update().get(id=variant_id)

        ProductVariantModel.objects.filter(
            product=variant.product,
            is_default=True,
        ).exclude(id=variant.id).update(is_default=False)

        variant.is_default = True
        variant.save(update_fields=["is_default", "updated_at"])
        return variant

    @staticmethod
    def update_variant(variant_id: uuid.UUID, **kwargs) -> ProductVariantModel:
        variant = ProductVariantModel.objects.get(id=variant_id)

        if "sku" in kwargs and kwargs["sku"] != variant.sku:
            if ProductVariantModel.objects.filter(sku=kwargs["sku"]).exists():
                raise ValidationError(f"SKU '{kwargs['sku']}' already exists")

        for field, value in kwargs.items():
            setattr(variant, field, value)

        variant.full_clean()
        variant.save()
        return variant


class ProductMediaService:
    """Service for product media operations."""

    @staticmethod
    def create_media(
        media_url: str,
        product_id: Optional[uuid.UUID] = None,
        variant_id: Optional[uuid.UUID] = None,
        alt_text: str = "",
        sort_order: int = 0,
        is_primary: bool = False,
    ) -> ProductMediaModel:
        if not product_id and not variant_id:
            raise ValidationError("Either product_id or variant_id must be provided")

        if product_id and variant_id:
            raise ValidationError("Only one of product_id or variant_id can be provided")

        media = ProductMediaModel.objects.create(
            media_url=media_url,
            product_id=product_id,
            variant_id=variant_id,
            alt_text=alt_text,
            sort_order=sort_order,
            is_primary=is_primary,
        )
        return media

    @staticmethod
    def update_media(media_id: uuid.UUID, **kwargs) -> ProductMediaModel:
        media = ProductMediaModel.objects.get(id=media_id)

        for field, value in kwargs.items():
            setattr(media, field, value)

        media.full_clean()
        media.save()
        return media


# Backward-compatible aliases for earlier service names.
CategoryService = CategoryCommandService
ProductService = ProductCommandService
