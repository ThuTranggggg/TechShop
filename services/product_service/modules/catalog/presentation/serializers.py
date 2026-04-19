"""Presentation serializers for catalog APIs."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from ..application.dtos import CategoryUpsertDTO, ProductUpsertDTO
from ..domain.enums import CategoryStatus, ProductStatus
from ..infrastructure.models import (
    BrandModel,
    CategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductTypeModel,
    ProductVariantModel,
)


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer for list/detail responses."""

    image = serializers.CharField(source="image_url", read_only=True)
    status = serializers.CharField(read_only=True)
    parent_slug = serializers.CharField(source="parent.slug", read_only=True)
    children_count = serializers.IntegerField(read_only=True)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CategoryModel
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "parent_slug",
            "description",
            "image",
            "image_url",
            "status",
            "is_active",
            "sort_order",
            "children_count",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CategoryWriteSerializer(serializers.Serializer):
    """Request validation for category create/update."""

    name = serializers.CharField(max_length=255, required=False)
    slug = serializers.SlugField(max_length=255, required=False)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=CategoryModel.objects.all(),
        allow_null=True,
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    image = serializers.URLField(required=False, allow_blank=True)
    image_url = serializers.URLField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[choice.value for choice in CategoryStatus],
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    sort_order = serializers.IntegerField(required=False)

    def validate_slug(self, value: str) -> str:
        instance = self.instance
        queryset = CategoryModel.objects.filter(slug=value)
        if instance:
            queryset = queryset.exclude(id=instance.id)
        if queryset.exists():
            raise serializers.ValidationError(f"Category with slug '{value}' already exists")
        return value

    def validate(self, attrs):
        instance = self.instance

        if instance and self.partial:
            attrs = {
                "name": attrs.get("name", instance.name),
                "slug": attrs.get("slug", instance.slug),
                "parent": attrs.get("parent", instance.parent),
                "description": attrs.get("description", instance.description),
                "image": attrs.get("image", None),
                "image_url": attrs.get("image_url", instance.image_url),
                "status": attrs.get("status", instance.status),
                "is_active": attrs.get("is_active", instance.is_active),
                "sort_order": attrs.get("sort_order", instance.sort_order),
            }
        else:
            attrs = {
                "name": attrs.get("name"),
                "slug": attrs.get("slug"),
                "parent": attrs.get("parent"),
                "description": attrs.get("description", ""),
                "image": attrs.get("image"),
                "image_url": attrs.get("image_url", ""),
                "status": attrs.get("status"),
                "is_active": attrs.get("is_active"),
                "sort_order": attrs.get("sort_order", 0),
            }

        image_url = attrs.get("image") if attrs.get("image") is not None else attrs.get("image_url", "")
        status_value = attrs.get("status")
        is_active = attrs.get("is_active")
        if status_value is None and is_active is None:
            status_value = CategoryStatus.ACTIVE.value
        elif status_value is None:
            status_value = CategoryStatus.ACTIVE.value if is_active else CategoryStatus.INACTIVE.value

        attrs["image_url"] = image_url
        attrs["status"] = status_value
        attrs["is_active"] = status_value == CategoryStatus.ACTIVE.value
        attrs.pop("image", None)

        parent = attrs.get("parent")
        if parent and instance:
            current = parent
            while current:
                if current.id == instance.id:
                    raise serializers.ValidationError("Circular category reference not allowed")
                current = current.parent

        if not attrs.get("name"):
            raise serializers.ValidationError({"name": ["This field is required."]})
        if not attrs.get("slug"):
            raise serializers.ValidationError({"slug": ["This field is required."]})

        return attrs

    def to_dto(self) -> CategoryUpsertDTO:
        validated = self.validated_data
        return CategoryUpsertDTO(
            name=validated["name"],
            slug=validated["slug"],
            parent_id=str(validated["parent"].id) if validated.get("parent") else None,
            description=validated.get("description", ""),
            image_url=validated.get("image_url", ""),
            status=validated["status"],
            sort_order=validated.get("sort_order", 0),
        )


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
        read_only_fields = fields

    @staticmethod
    def get_products_count(obj) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE.value, is_active=True).count()


class BrandCreateUpdateSerializer(serializers.ModelSerializer):
    """Brand serializer for create/update."""

    class Meta:
        model = BrandModel
        fields = ["name", "slug", "description", "logo_url", "is_active"]

    def validate_slug(self, value: str) -> str:
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
        read_only_fields = fields

    @staticmethod
    def get_products_count(obj) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE.value, is_active=True).count()


class ProductTypeCreateUpdateSerializer(serializers.ModelSerializer):
    """Product type serializer for create/update."""

    class Meta:
        model = ProductTypeModel
        fields = ["code", "name", "description", "is_active"]

    def validate_code(self, value: str) -> str:
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
        read_only_fields = fields


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
        read_only_fields = fields

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
        instance = self.instance
        if ProductVariantModel.objects.filter(sku=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError(f"SKU '{value}' already exists")
        return value

    def validate(self, data):
        if data.get("is_default"):
            product = self.instance.product if self.instance else None
            if not product:
                product_id = self.context.get("product_id")
                if ProductVariantModel.objects.filter(product_id=product_id, is_default=True).exists():
                    raise serializers.ValidationError("Product already has a default variant")
            else:
                if ProductVariantModel.objects.filter(product=product, is_default=True).exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError("Product already has a default variant")
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer."""

    price = serializers.DecimalField(source="base_price", max_digits=12, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    product_type_code = serializers.CharField(source="product_type.code", read_only=True)
    variants_count = serializers.SerializerMethodField()
    default_sku = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "category",
            "category_name",
            "category_slug",
            "brand",
            "brand_name",
            "product_type",
            "product_type_name",
            "product_type_code",
            "base_price",
            "price",
            "currency",
            "stock",
            "rating",
            "tags",
            "status",
            "is_active",
            "is_featured",
            "thumbnail_url",
            "default_sku",
            "variants_count",
            "published_at",
            "created_at",
        ]
        read_only_fields = fields

    @staticmethod
    def get_variants_count(obj) -> int:
        cached_variants = getattr(obj, "_prefetched_objects_cache", {}).get("variants")
        if cached_variants is not None:
            return len([variant for variant in cached_variants if variant.is_active])
        return obj.variants.filter(is_active=True).count()

    @staticmethod
    def get_default_sku(obj) -> str | None:
        default_variant = obj.default_variant
        return default_variant.sku if default_variant else None

    @staticmethod
    def get_stock(obj) -> int:
        return int(obj.attributes.get("stock", 0) or 0)

    @staticmethod
    def get_rating(obj) -> float:
        return float(obj.attributes.get("rating", 0) or 0)

    @staticmethod
    def get_tags(obj) -> list[str]:
        tags = obj.attributes.get("tags", [])
        return tags if isinstance(tags, list) else []


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer."""

    price = serializers.DecimalField(source="base_price", max_digits=12, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    product_type_code = serializers.CharField(source="product_type.code", read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    default_sku = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

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
            "category_slug",
            "brand",
            "brand_name",
            "product_type",
            "product_type_name",
            "product_type_code",
            "base_price",
            "price",
            "currency",
            "stock",
            "rating",
            "tags",
            "attributes",
            "status",
            "is_active",
            "is_featured",
            "thumbnail_url",
            "default_sku",
            "seo_title",
            "seo_description",
            "variants",
            "media",
            "images",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @staticmethod
    def get_images(obj) -> list[str]:
        cached_media = getattr(obj, "_prefetched_objects_cache", {}).get("media")
        if cached_media is not None:
            return [item.media_url for item in cached_media]
        return list(obj.media.values_list("media_url", flat=True))

    @staticmethod
    def get_default_sku(obj) -> str | None:
        default_variant = obj.default_variant
        return default_variant.sku if default_variant else None

    @staticmethod
    def get_stock(obj) -> int:
        return int(obj.attributes.get("stock", 0) or 0)

    @staticmethod
    def get_rating(obj) -> float:
        return float(obj.attributes.get("rating", 0) or 0)

    @staticmethod
    def get_tags(obj) -> list[str]:
        tags = obj.attributes.get("tags", [])
        return tags if isinstance(tags, list) else []


class ProductWriteSerializer(serializers.Serializer):
    """Request validation for product create/update."""

    name = serializers.CharField(max_length=255, required=False)
    slug = serializers.SlugField(max_length=255, required=False)
    short_description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(queryset=CategoryModel.objects.all(), required=False)
    brand = serializers.PrimaryKeyRelatedField(queryset=BrandModel.objects.all(), required=False, allow_null=True)
    product_type = serializers.PrimaryKeyRelatedField(queryset=ProductTypeModel.objects.all(), required=False)
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    attributes = serializers.JSONField(required=False)
    status = serializers.ChoiceField(
        choices=[choice.value for choice in ProductStatus],
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    thumbnail_url = serializers.URLField(required=False, allow_blank=True)
    seo_title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    seo_description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_slug(self, value: str) -> str:
        instance = self.instance
        queryset = ProductModel.objects.filter(slug=value)
        if instance:
            queryset = queryset.exclude(id=instance.id)
        if queryset.exists():
            raise serializers.ValidationError(f"Product with slug '{value}' already exists")
        return value

    def validate_base_price(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("Base price must be greater than 0")
        return value

    def validate(self, attrs):
        instance = self.instance

        if instance and self.partial:
            attrs = {
                "name": attrs.get("name", instance.name),
                "slug": attrs.get("slug", instance.slug),
                "short_description": attrs.get("short_description", instance.short_description),
                "description": attrs.get("description", instance.description),
                "category": attrs.get("category", instance.category),
                "brand": attrs.get("brand", instance.brand),
                "product_type": attrs.get("product_type", instance.product_type),
                "base_price": attrs.get("base_price", instance.base_price),
                "currency": attrs.get("currency", instance.currency),
                "attributes": attrs.get("attributes", instance.attributes),
                "status": attrs.get("status", instance.status),
                "is_active": attrs.get("is_active", instance.is_active),
                "is_featured": attrs.get("is_featured", instance.is_featured),
                "thumbnail_url": attrs.get("thumbnail_url", instance.thumbnail_url),
                "seo_title": attrs.get("seo_title", instance.seo_title),
                "seo_description": attrs.get("seo_description", instance.seo_description),
            }

        required_fields = ("name", "slug", "category", "product_type", "base_price")
        missing_fields = [field for field in required_fields if attrs.get(field) in (None, "")]
        if missing_fields:
            raise serializers.ValidationError({field: ["This field is required."] for field in missing_fields})

        return attrs

    def to_dto(self) -> ProductUpsertDTO:
        validated = self.validated_data
        return ProductUpsertDTO(
            name=validated["name"],
            slug=validated["slug"],
            short_description=validated.get("short_description", ""),
            description=validated.get("description", ""),
            category_id=str(validated["category"].id),
            brand_id=str(validated["brand"].id) if validated.get("brand") else None,
            product_type_id=str(validated["product_type"].id),
            base_price=validated["base_price"],
            currency=validated.get("currency", "VND"),
            attributes=validated.get("attributes", {}),
            status=validated.get("status", ProductStatus.DRAFT.value),
            is_active=validated.get("is_active", True),
            is_featured=validated.get("is_featured", False),
            thumbnail_url=validated.get("thumbnail_url", ""),
            seo_title=validated.get("seo_title", ""),
            seo_description=validated.get("seo_description", ""),
        )


class ProductSnapshotSerializer(serializers.Serializer):
    """Snapshot of product for internal APIs."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    category_slug = serializers.CharField()
    brand_id = serializers.UUIDField(required=False, allow_null=True)
    brand_name = serializers.CharField(required=False, allow_null=True)
    product_type = serializers.CharField()
    base_price = serializers.FloatField()
    currency = serializers.CharField()
    thumbnail_url = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    is_active = serializers.BooleanField()
    is_featured = serializers.BooleanField()
    attributes = serializers.JSONField()
    default_variant = serializers.JSONField(required=False, allow_null=True)


class InternalProductBulkSerializer(serializers.Serializer):
    """Bulk product lookup for internal APIs."""

    product_ids = serializers.ListField(child=serializers.UUIDField(), help_text="List of product IDs to retrieve")
    include_variants = serializers.BooleanField(default=False, required=False)
    include_media = serializers.BooleanField(default=False, required=False)


class InternalVariantBulkSerializer(serializers.Serializer):
    """Bulk variant lookup for internal APIs."""

    variant_ids = serializers.ListField(child=serializers.UUIDField(), help_text="List of variant IDs to retrieve")
