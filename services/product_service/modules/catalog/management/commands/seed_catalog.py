"""Seed multi-category catalog data for product-service."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.catalog.application.seed_data import (
    BRAND_SEED_DATA,
    CATEGORY_SEED_DATA,
    PRODUCT_SEED_DATA,
    PRODUCT_TYPE_SEED_DATA,
    product_image,
    stable_uuid,
)
from modules.catalog.domain.enums import CategoryStatus, ProductStatus
from modules.catalog.infrastructure.models import (
    BrandModel,
    CategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductTypeModel,
    ProductVariantModel,
)


class Command(BaseCommand):
    help = "Seed 10+ categories and sample products into product-service."

    def handle(self, *args, **options):
        categories = {}
        for item in CATEGORY_SEED_DATA:
            category, _ = CategoryModel.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "id": UUID(item["id"]),
                    "name": item["name"],
                    "description": item["description"],
                    "image_url": item["image_url"],
                    "status": CategoryStatus.ACTIVE.value,
                    "is_active": True,
                    "sort_order": item["sort_order"],
                    "parent": None,
                },
            )
            categories[item["slug"]] = category

        brands = {}
        for item in BRAND_SEED_DATA:
            brand, _ = BrandModel.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "id": UUID(item["id"]),
                    "name": item["name"],
                    "description": f"{item['name']} sample brand for catalog seed.",
                    "logo_url": f"https://picsum.photos/seed/{item['slug']}/360/360",
                    "is_active": True,
                },
            )
            brands[item["slug"]] = brand

        product_types = {}
        for item in PRODUCT_TYPE_SEED_DATA:
            product_type, _ = ProductTypeModel.objects.update_or_create(
                code=item["code"],
                defaults={
                    "id": UUID(item["id"]),
                    "name": item["name"],
                    "description": f"{item['name']} sample product type.",
                    "is_active": True,
                },
            )
            product_types[item["code"]] = product_type

        for item in PRODUCT_SEED_DATA:
            category = categories[item["category_slug"]]
            brand = brands[item["brand_slug"]]
            product_type = product_types[item["product_type_code"]]
            stock = int(item.get("stock", 25))
            rating = float(item.get("rating", 4.5))
            tags = item.get("tags", [])
            item_type = item.get("item_type", product_type.code.lower())
            short_description = item.get(
                "short_description",
                f"{item['name']} for {item_type.replace('_', ' ')} needs in {category.name.lower()}.",
            )
            description = item.get(
                "description",
                (
                    f"{item['name']} belongs to {category.name} with {brand.name} branding. "
                    f"It is seeded for TechShop demos covering search, cart, checkout, RAG chat, "
                    f"behavior analytics and cross-category recommendations."
                ),
            )
            thumbnail_url = product_image(item["product_type_code"], item["category_slug"])

            product, _ = ProductModel.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "id": UUID(stable_uuid("product", item["slug"])),
                    "name": item["name"],
                    "short_description": short_description,
                    "description": description,
                    "category": category,
                    "brand": brand,
                    "product_type": product_type,
                    "base_price": Decimal(item["price"]),
                    "currency": "VND",
                    "attributes": {
                        "seeded": True,
                        "category": category.slug,
                        "brand": brand.slug,
                        "product_type_code": product_type.code,
                        "item_type": item_type,
                        "tags": tags,
                        "rating": rating,
                        "stock": stock,
                    },
                    "status": ProductStatus.ACTIVE.value,
                    "is_active": True,
                    "is_featured": item["featured"],
                    "thumbnail_url": thumbnail_url,
                    "seo_title": f"{item['name']} | {category.name}",
                    "seo_description": f"Discover {item['name']} in the {category.name} category with {brand.name}.",
                    "published_at": timezone.now(),
                },
            )

            ProductVariantModel.objects.update_or_create(
                sku=f"{item['slug'].upper().replace('-', '')}-STD",
                defaults={
                    "id": UUID(stable_uuid("variant", item["slug"])),
                    "product": product,
                    "name": "Standard",
                    "attributes": {"size": "standard", "tags": tags, "item_type": item_type},
                    "price_override": Decimal(item["price"]),
                    "barcode": f"BAR{item['slug'].upper().replace('-', '')}",
                    "is_default": True,
                    "is_active": True,
                },
            )

            product.variants.exclude(sku=f"{item['slug'].upper().replace('-', '')}-STD").update(is_default=False)

            ProductMediaModel.objects.update_or_create(
                product=product,
                variant=None,
                sort_order=0,
                defaults={
                    "id": UUID(stable_uuid("media", item["slug"])),
                    "media_url": thumbnail_url,
                    "alt_text": item["name"],
                    "is_primary": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {CategoryModel.objects.count()} categories and {ProductModel.objects.count()} products."
            )
        )
