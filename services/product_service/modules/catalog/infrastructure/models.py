"""
Infrastructure layer - Django ORM models for Catalog context.

Maps domain entities to database persistence.
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError

from ..domain.enums import ProductStatus, Currency, AttributeType, MediaType


class CategoryModel(models.Model):
    """Category model - hierarchy support."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_category"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "sort_order"]),
            models.Index(fields=["parent"]),
        ]
        ordering = ["sort_order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def clean(self):
        """Prevent circular parent references."""
        if self.parent_id and self.id:
            if self.parent_id == self.id:
                raise ValidationError("Category cannot be its own parent")
            # Check for circular references
            current = self.parent
            visited = set()
            while current:
                if current.id in visited:
                    raise ValidationError("Circular category reference detected")
                if current.id == self.id:
                    raise ValidationError("Circular category reference detected")
                visited.add(current.id)
                current = current.parent

    def get_all_children(self):
        """Get all descendant categories."""
        children = list(self.children.all())
        for child in list(self.children.all()):
            children.extend(child.get_all_children())
        return children


class BrandModel(models.Model):
    """Brand model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    description = models.TextField(blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_brand"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name


class ProductTypeModel(models.Model):
    """Product type model for classification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(unique=True, max_length=100, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product_type"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["name"]
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"

    def __str__(self):
        return self.name


class ProductModel(models.Model):
    """Product model - main aggregate root."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    short_description = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    
    category = models.ForeignKey(
        CategoryModel,
        on_delete=models.PROTECT,
        related_name="products",
    )
    brand = models.ForeignKey(
        BrandModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    product_type = models.ForeignKey(
        ProductTypeModel,
        on_delete=models.PROTECT,
        related_name="products",
    )
    
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        choices=[(c.value, c.name) for c in Currency],
        default=Currency.VND.value,
    )
    
    # Flexible attributes as JSON
    attributes = models.JSONField(default=dict, blank=True)
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ProductStatus],
        default=ProductStatus.DRAFT.value,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # SEO and media
    thumbnail_url = models.URLField(blank=True, default="")
    seo_title = models.CharField(max_length=255, blank=True, default="")
    seo_description = models.CharField(max_length=500, blank=True, default="")
    
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["category"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["product_type"]),
            models.Index(fields=["base_price"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["published_at"]),
            models.Index(fields=["created_at", "-id"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    @property
    def is_published(self) -> bool:
        """Check if product is published and visible to public."""
        return (
            self.status == ProductStatus.ACTIVE.value
            and self.is_active
            and self.published_at is not None
        )

    def publish(self):
        """Publish product."""
        if self.status == ProductStatus.DRAFT.value:
            self.status = ProductStatus.ACTIVE.value
            self.published_at = models.F('updated_at')  # Will be set on save

    def unpublish(self):
        """Unpublish product."""
        if self.status == ProductStatus.ACTIVE.value:
            self.status = ProductStatus.DRAFT.value

    def activate(self):
        """Activate product."""
        self.is_active = True

    def deactivate(self):
        """Deactivate product."""
        self.is_active = False


class ProductVariantModel(models.Model):
    """Product variant model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    sku = models.CharField(
        unique=True,
        max_length=100,
        db_index=True,
    )
    name = models.CharField(max_length=255, db_index=True)
    
    # Variant-specific attributes
    attributes = models.JSONField(default=dict, blank=True)
    
    # Price override
    price_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    
    # Physical properties
    barcode = models.CharField(max_length=100, blank=True, default="", unique=True)
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    
    # Status
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product_variant"
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["product"]),
            models.Index(fields=["product", "is_default"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "is_default"],
                condition=models.Q(is_default=True),
                name="one_default_variant_per_product",
            )
        ]
        ordering = ["-is_default", "name"]
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def clean(self):
        """Validate variant constraints."""
        # Check if setting is_default and there's already a default
        if self.is_default:
            existing_default = ProductVariantModel.objects.filter(
                product=self.product,
                is_default=True
            ).exclude(id=self.id).exists()
            if existing_default:
                raise ValidationError("This product already has a default variant")

    def get_effective_price(self) -> float:
        """Get effective price: override or product base_price."""
        return float(self.price_override or self.product.base_price)


class ProductMediaModel(models.Model):
    """Product media/image model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media",
    )
    variant = models.ForeignKey(
        ProductVariantModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media",
    )
    
    media_url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product_media"
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["variant"]),
            models.Index(fields=["is_primary"]),
            models.Index(fields=["sort_order"]),
        ]
        ordering = ["sort_order", "-is_primary"]
        verbose_name = "Product Media"
        verbose_name_plural = "Product Media"

    def __str__(self):
        return f"Media for {self.product or self.variant}"

    def clean(self):
        """Ensure either product or variant is set, but not both."""
        if self.product and self.variant:
            raise ValidationError("Media must be linked to either product OR variant, not both")
        if not self.product and not self.variant:
            raise ValidationError("Media must be linked to either product OR variant")
