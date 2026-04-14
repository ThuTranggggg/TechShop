"""
Application services for Catalog context.

Orchestrates use cases and domain logic.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from django.db import transaction
from django.core.exceptions import ValidationError

from ..domain.enums import ProductStatus, Currency
from ..domain.entities import Slug, Money, SKU
from ..infrastructure.models import (
    CategoryModel,
    BrandModel,
    ProductTypeModel,
    ProductModel,
    ProductVariantModel,
    ProductMediaModel,
)


class CategoryService:
    """Service for category operations."""

    @staticmethod
    def create_category(
        name: str,
        slug: str,
        parent_id: Optional[uuid.UUID] = None,
        description: str = "",
        image_url: str = "",
        is_active: bool = True,
        sort_order: int = 0,
    ) -> CategoryModel:
        """Create a new category."""
        # Validate slug
        if CategoryModel.objects.filter(slug=slug).exists():
            raise ValidationError(f"Category with slug '{slug}' already exists")

        # Prevent circular reference
        if parent_id:
            parent = CategoryModel.objects.get(id=parent_id)
            # Check if parent exists in descendants
            category_to_check = parent
            visited = set()
            while category_to_check:
                if category_to_check.id in visited:
                    raise ValidationError("Circular category reference")
                visited.add(category_to_check.id)
                category_to_check = category_to_check.parent

        category = CategoryModel.objects.create(
            name=name,
            slug=slug,
            parent_id=parent_id,
            description=description,
            image_url=image_url,
            is_active=is_active,
            sort_order=sort_order,
        )
        return category

    @staticmethod
    def update_category(
        category_id: uuid.UUID,
        **kwargs
    ) -> CategoryModel:
        """Update category."""
        category = CategoryModel.objects.get(id=category_id)
        
        # Check for slug uniqueness if changing slug
        if "slug" in kwargs and kwargs["slug"] != category.slug:
            if CategoryModel.objects.filter(slug=kwargs["slug"]).exists():
                raise ValidationError(f"Slug '{kwargs['slug']}' already exists")

        for field, value in kwargs.items():
            setattr(category, field, value)
        
        category.full_clean()
        category.save()
        return category


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
        """Create a new brand."""
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
        """Update brand."""
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
        """Create a new product type."""
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
        """Update product type."""
        product_type = ProductTypeModel.objects.get(id=product_type_id)
        
        if "code" in kwargs and kwargs["code"] != product_type.code:
            if ProductTypeModel.objects.filter(code=kwargs["code"]).exists():
                raise ValidationError(f"Code '{kwargs['code']}' already exists")

        for field, value in kwargs.items():
            setattr(product_type, field, value)

        product_type.save()
        return product_type


class ProductService:
    """Service for product operations."""

    @staticmethod
    @transaction.atomic
    def create_product(
        name: str,
        slug: str,
        category_id: uuid.UUID,
        product_type_id: uuid.UUID,
        base_price: float,
        currency: str = "VND",
        brand_id: Optional[uuid.UUID] = None,
        short_description: str = "",
        description: str = "",
        attributes: Dict[str, Any] = None,
        status: str = "draft",
        is_active: bool = True,
        is_featured: bool = False,
        thumbnail_url: str = "",
        seo_title: str = "",
        seo_description: str = "",
    ) -> ProductModel:
        """Create a new product."""
        # Validate slug uniqueness
        if ProductModel.objects.filter(slug=slug).exists():
            raise ValidationError(f"Product with slug '{slug}' already exists")

        # Validate category and product_type exist
        category = CategoryModel.objects.get(id=category_id)
        product_type = ProductTypeModel.objects.get(id=product_type_id)

        if brand_id:
            brand = BrandModel.objects.get(id=brand_id)

        product = ProductModel.objects.create(
            name=name,
            slug=slug,
            short_description=short_description,
            description=description,
            category=category,
            brand_id=brand_id,
            product_type=product_type,
            base_price=base_price,
            currency=currency,
            attributes=attributes or {},
            status=status,
            is_active=is_active,
            is_featured=is_featured,
            thumbnail_url=thumbnail_url,
            seo_title=seo_title,
            seo_description=seo_description,
        )
        return product

    @staticmethod
    def update_product(product_id: uuid.UUID, **kwargs) -> ProductModel:
        """Update product."""
        product = ProductModel.objects.get(id=product_id)
        
        # Can't change slug to existing one
        if "slug" in kwargs and kwargs["slug"] != product.slug:
            if ProductModel.objects.filter(slug=kwargs["slug"]).exists():
                raise ValidationError(f"Slug '{kwargs['slug']}' already exists")

        for field, value in kwargs.items():
            setattr(product, field, value)

        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def publish_product(product_id: uuid.UUID) -> ProductModel:
        """Publish product."""
        product = ProductModel.objects.select_for_update().get(id=product_id)
        
        if product.status != ProductStatus.DRAFT.value:
            raise ValidationError("Only draft products can be published")

        product.status = ProductStatus.ACTIVE.value
        product.published_at = datetime.utcnow()
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def unpublish_product(product_id: uuid.UUID) -> ProductModel:
        """Unpublish product."""
        product = ProductModel.objects.select_for_update().get(id=product_id)
        
        if product.status != ProductStatus.ACTIVE.value:
            raise ValidationError("Only active products can be unpublished")

        product.status = ProductStatus.DRAFT.value
        product.save()
        return product

    @staticmethod
    def activate_product(product_id: uuid.UUID) -> ProductModel:
        """Activate product."""
        product = ProductModel.objects.get(id=product_id)
        product.is_active = True
        product.save()
        return product

    @staticmethod
    def deactivate_product(product_id: uuid.UUID) -> ProductModel:
        """Deactivate product."""
        product = ProductModel.objects.get(id=product_id)
        product.is_active = False
        product.save()
        return product

    @staticmethod
    def get_product_snapshot(product_id: uuid.UUID) -> Dict[str, Any]:
        """Get product snapshot for internal APIs (cart, order, etc)."""
        product = ProductModel.objects.select_related(
            "category", "brand", "product_type"
        ).prefetch_related("variants", "media").get(id=product_id)

        default_variant = product.variants.filter(is_default=True).first()

        return {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "category_id": str(product.category.id),
            "category_name": product.category.name,
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
        """Create a new product variant."""
        product = ProductModel.objects.get(id=product_id)
        
        # Check SKU uniqueness
        if ProductVariantModel.objects.filter(sku=sku).exists():
            raise ValidationError(f"SKU '{sku}' already exists")

        # Check for default variant
        if is_default:
            existing_default = ProductVariantModel.objects.filter(
                product=product, is_default=True
            ).exists()
            if existing_default:
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
        """Set variant as default."""
        variant = ProductVariantModel.objects.select_for_update().get(id=variant_id)
        
        # Clear current default
        ProductVariantModel.objects.filter(
            product=variant.product,
            is_default=True
        ).exclude(id=variant.id).update(is_default=False)

        # Set new default
        variant.is_default = True
        variant.save()
        return variant

    @staticmethod
    def update_variant(variant_id: uuid.UUID, **kwargs) -> ProductVariantModel:
        """Update variant."""
        variant = ProductVariantModel.objects.get(id=variant_id)
        
        # Check SKU uniqueness if changing
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
        """Create product media."""
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
        """Update media."""
        media = ProductMediaModel.objects.get(id=media_id)
        
        for field, value in kwargs.items():
            setattr(media, field, value)

        media.full_clean()
        media.save()
        return media
