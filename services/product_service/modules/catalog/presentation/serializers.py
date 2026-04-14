"""
Presentation layer serializers for Catalog API.

Request/response validation and transformation.
"""
from typing import Dict, Any, Optional
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from ..domain.enums import ProductStatus, Currency
from ..infrastructure.models import (
    CategoryModel,
    BrandModel,
    ProductTypeModel,
    ProductModel,
    ProductVariantModel,
    ProductMediaModel,
)


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer for read operations."""
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = CategoryModel
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "image_url",
            "is_active",
            "sort_order",
            "children_count",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    @staticmethod
    def get_children_count(obj) -> int:
        return obj.children.filter(is_active=True).count()

    @staticmethod
    def get_products_count(obj) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE.value, is_active=True).count()


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    """Category serializer for create/update operations."""

    class Meta:
        model = CategoryModel
        fields = [
            "name",
            "slug",
            "parent",
            "description",
            "image_url",
            "is_active",
            "sort_order",
        ]

    def validate_slug(self, value: str) -> str:
        """Validate slug is unique."""
        instance = self.instance
        if CategoryModel.objects.filter(slug=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"Category with slug '{value}' already exists")
        return value

    def validate(self, data):
        """Validate parent doesn't create circular reference."""
        parent_id = data.get("parent")
        instance = self.instance

        if parent_id:
            # Check circular reference
            current = parent_id
            visited = set()
            while current:
                if current.id == (instance.id if instance else None):
                    raise serializers.ValidationError("Circular category reference not allowed")
                if current.id in visited:
                    raise serializers.ValidationError("Circular category reference not allowed")
                visited.add(current.id)
                current = current.parent

        return data


class BrandSerializer(serializers.ModelSerializer):
    """Brand serializer."""
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = BrandModel
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "logo_url",
            "is_active",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    @staticmethod
    def get_products_count(obj) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE.value, is_active=True).count()


class BrandCreateUpdateSerializer(serializers.ModelSerializer):
    """Brand serializer for create/update."""

    class Meta:
        model = BrandModel
        fields = ["name", "slug", "description", "logo_url", "is_active"]

    def validate_slug(self, value: str) -> str:
        """Validate slug is unique."""
        instance = self.instance
        if BrandModel.objects.filter(slug=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"Brand with slug '{value}' already exists")
        return value


class ProductTypeSerializer(serializers.ModelSerializer):
    """Product type serializer."""
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductTypeModel
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    @staticmethod
    def get_products_count(obj) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE.value, is_active=True).count()


class ProductTypeCreateUpdateSerializer(serializers.ModelSerializer):
    """Product type serializer for create/update."""

    class Meta:
        model = ProductTypeModel
        fields = ["code", "name", "description", "is_active"]

    def validate_code(self, value: str) -> str:
        """Validate code is unique."""
        instance = self.instance
        if ProductTypeModel.objects.filter(code=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"Product type with code '{value}' already exists")
        return value


class ProductMediaSerializer(serializers.ModelSerializer):
    """Product media serializer."""

    class Meta:
        model = ProductMediaModel
        fields = [
            "id",
            "media_url",
            "alt_text",
            "sort_order",
            "is_primary",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ProductMediaCreateUpdateSerializer(serializers.ModelSerializer):
    """Product media create/update serializer."""

    class Meta:
        model = ProductMediaModel
        fields = ["media_url", "alt_text", "sort_order", "is_primary"]


class ProductVariantSerializer(serializers.ModelSerializer):
    """Product variant serializer."""
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariantModel
        fields = [
            "id",
            "sku",
            "name",
            "attributes",
            "price_override",
            "compare_at_price",
            "effective_price",
            "barcode",
            "weight",
            "is_default",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["created_at", "effective_price"]

    @staticmethod
    def get_effective_price(obj) -> float:
        return obj.get_effective_price()


class ProductVariantCreateUpdateSerializer(serializers.ModelSerializer):
    """Product variant create/update serializer."""

    class Meta:
        model = ProductVariantModel
        fields = [
            "sku",
            "name",
            "attributes",
            "price_override",
            "compare_at_price",
            "barcode",
            "weight",
            "is_default",
            "is_active",
        ]

    def validate_sku(self, value: str) -> str:
        """Validate SKU is unique."""
        instance = self.instance
        if ProductVariantModel.objects.filter(sku=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"SKU '{value}' already exists")
        return value

    def validate(self, data):
        """Validate variant constraints."""
        if data.get("is_default"):
            product = self.instance.product if self.instance else None
            if not product:
                # For create, product_id should be in context
                product_id = self.context.get("product_id")
                if ProductVariantModel.objects.filter(
                    product_id=product_id, is_default=True
                ).exists():
                    raise serializers.ValidationError("Product already has a default variant")
            else:
                # For update
                if ProductVariantModel.objects.filter(
                    product=product, is_default=True
                ).exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError("Product already has a default variant")
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer (public and admin)."""
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    variants_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "category",
            "category_name",
            "brand",
            "brand_name",
            "product_type_name",
            "base_price",
            "currency",
            "status",
            "is_active",
            "is_featured",
            "thumbnail_url",
            "variants_count",
            "published_at",
            "created_at",
        ]
        read_only_fields = ["created_at", "published_at"]

    @staticmethod
    def get_variants_count(obj) -> int:
        return obj.variants.filter(is_active=True).count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer."""
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)

    class Meta:
        model = ProductModel
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "category",
            "category_name",
            "brand",
            "brand_name",
            "product_type_name",
            "base_price",
            "currency",
            "attributes",
            "status",
            "is_active",
            "is_featured",
            "thumbnail_url",
            "seo_title",
            "seo_description",
            "variants",
            "media",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "published_at",
            "status",
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product create/update serializer."""

    class Meta:
        model = ProductModel
        fields = [
            "name",
            "slug",
            "short_description",
            "description",
            "category",
            "brand",
            "product_type",
            "base_price",
            "currency",
            "attributes",
            "is_active",
            "is_featured",
            "thumbnail_url",
            "seo_title",
            "seo_description",
        ]

    def validate_slug(self, value: str) -> str:
        """Validate slug is unique."""
        instance = self.instance
        if ProductModel.objects.filter(slug=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"Product with slug '{value}' already exists")
        return value

    def validate_base_price(self, value: float) -> float:
        """Validate price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Base price must be greater than 0")
        return value


class ProductSnapshotSerializer(serializers.Serializer):
    """Snapshot of product for internal APIs (cart, order, etc)."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    brand_id = serializers.UUIDField(required=False, allow_null=True)
    brand_name = serializers.CharField(required=False, allow_null=True)
    product_type = serializers.CharField()
    base_price = serializers.FloatField()
    currency = serializers.CharField()
    thumbnail_url = serializers.URLField()
    status = serializers.CharField()
    is_active = serializers.BooleanField()
    is_featured = serializers.BooleanField()
    attributes = serializers.JSONField()
    default_variant = serializers.JSONField(required=False, allow_null=True)


class InternalProductBulkSerializer(serializers.Serializer):
    """Bulk product lookup for internal APIs."""
    product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of product IDs to retrieve"
    )
    include_variants = serializers.BooleanField(default=False, required=False)
    include_media = serializers.BooleanField(default=False, required=False)


class InternalVariantBulkSerializer(serializers.Serializer):
    """Bulk variant lookup for internal APIs."""
    variant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of variant IDs to retrieve"
    )
