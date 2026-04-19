from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from modules.catalog.domain.enums import CategoryStatus, ProductStatus
from modules.catalog.infrastructure.models import (
    BrandModel,
    CategoryModel,
    ProductModel,
    ProductTypeModel,
)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_headers = {"HTTP_X_ADMIN": "true"}
        self.brand = BrandModel.objects.create(
            name="Seed Brand",
            slug="seed-brand",
            description="Brand",
            logo_url="https://example.com/brand.png",
            is_active=True,
        )
        self.product_type = ProductTypeModel.objects.create(
            code="GENERAL",
            name="General",
            description="General product type",
            is_active=True,
        )
        self.category = CategoryModel.objects.create(
            name="Dien tu",
            slug="dien-tu",
            description="Electronics",
            image_url="https://example.com/cat.png",
            status=CategoryStatus.ACTIVE.value,
            is_active=True,
            sort_order=1,
        )

    def _create_product(self, *, slug: str = "tai-nghe-orbit", category: CategoryModel | None = None) -> ProductModel:
        return ProductModel.objects.create(
            name="Tai nghe Orbit",
            slug=slug,
            short_description="Wireless audio",
            description="Sample product",
            category=category or self.category,
            brand=self.brand,
            product_type=self.product_type,
            base_price=Decimal("1299000"),
            currency="VND",
            attributes={"seeded": True},
            status=ProductStatus.ACTIVE.value,
            is_active=True,
            is_featured=True,
            thumbnail_url="https://example.com/product.png",
            seo_title="Tai nghe Orbit",
            seo_description="Sample description",
            published_at=timezone.now(),
        )

    def test_create_category_success(self):
        response = self.client.post(
            "/api/v1/catalog/admin/categories/",
            {
                "name": "Noi that",
                "slug": "noi-that",
                "description": "Furniture",
                "image_url": "https://example.com/noi-that.png",
                "status": "active",
                "sort_order": 2,
            },
            format="json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["slug"], "noi-that")
        self.assertTrue(CategoryModel.objects.filter(slug="noi-that", status="active").exists())

    def test_create_product_with_category_success(self):
        response = self.client.post(
            "/api/v1/catalog/admin/products/",
            {
                "name": "Sac nhanh 65W",
                "slug": "sac-nhanh-65w",
                "short_description": "Fast charger",
                "description": "GaN charger",
                "category": str(self.category.id),
                "brand": str(self.brand.id),
                "product_type": str(self.product_type.id),
                "base_price": "790000",
                "currency": "VND",
                "status": "active",
                "is_active": True,
                "thumbnail_url": "https://example.com/charger.png",
            },
            format="json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["category"], str(self.category.id))
        self.assertTrue(ProductModel.objects.filter(slug="sac-nhanh-65w", category=self.category).exists())

    def test_create_product_rejects_missing_category(self):
        response = self.client.post(
            "/api/v1/catalog/admin/products/",
            {
                "name": "Invalid product",
                "slug": "invalid-product",
                "short_description": "Invalid",
                "description": "Invalid",
                "category": str(uuid.uuid4()),
                "brand": str(self.brand.id),
                "product_type": str(self.product_type.id),
                "base_price": "100000",
                "currency": "VND",
            },
            format="json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ProductModel.objects.filter(slug="invalid-product").exists())

    def test_list_categories_success(self):
        CategoryModel.objects.create(
            name="Sach",
            slug="sach",
            description="Books",
            image_url="https://example.com/books.png",
            status=CategoryStatus.ACTIVE.value,
            is_active=True,
            sort_order=2,
        )

        response = self.client.get("/api/v1/catalog/categories/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 2)
        self.assertIn("results", payload)

    def test_list_products_by_category_success(self):
        self._create_product(slug="tai-nghe-orbit")
        self._create_product(slug="sac-nhanh-65w")

        response = self.client.get(f"/api/v1/catalog/categories/{self.category.slug}/products/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertTrue(all(item["category_slug"] == self.category.slug for item in payload["results"]))

    def test_product_pagination_and_category_filter_work(self):
        other_category = CategoryModel.objects.create(
            name="Sach",
            slug="sach",
            description="Books",
            image_url="https://example.com/books.png",
            status=CategoryStatus.ACTIVE.value,
            is_active=True,
            sort_order=3,
        )
        self._create_product(slug="tai-nghe-orbit")
        self._create_product(slug="sac-nhanh-65w")
        self._create_product(slug="combo-truyen", category=other_category)

        response = self.client.get(
            f"/api/v1/catalog/products/?category_slug={self.category.slug}&page_size=1&ordering=name"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["category_slug"], self.category.slug)

    def test_category_slug_must_be_unique(self):
        response = self.client.post(
            "/api/v1/catalog/admin/categories/",
            {
                "name": "Dien tu duplicate",
                "slug": "dien-tu",
                "status": "active",
            },
            format="json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_delete_category_if_products_exist(self):
        product = self._create_product()

        response = self.client.delete(
            f"/api/v1/catalog/admin/categories/{self.category.id}/",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(CategoryModel.objects.filter(id=self.category.id).exists())
        self.assertTrue(ProductModel.objects.filter(id=product.id).exists())

    def test_seed_catalog_creates_10_plus_categories(self):
        call_command("seed_catalog")

        self.assertGreaterEqual(CategoryModel.objects.count(), 12)
        self.assertGreaterEqual(ProductModel.objects.count(), 24)
        self.assertTrue(
            all(category.products.count() >= 2 for category in CategoryModel.objects.filter(status=CategoryStatus.ACTIVE.value))
        )

    def test_product_detail_by_id_keeps_backward_compatibility(self):
        product = self._create_product()

        response_by_id = self.client.get(f"/api/v1/catalog/products/{product.id}/")
        response_by_slug = self.client.get(f"/api/v1/catalog/products/{product.slug}/")

        self.assertEqual(response_by_id.status_code, 200)
        self.assertEqual(response_by_slug.status_code, 200)
        self.assertEqual(response_by_id.json()["id"], str(product.id))
        self.assertEqual(response_by_slug.json()["slug"], product.slug)

