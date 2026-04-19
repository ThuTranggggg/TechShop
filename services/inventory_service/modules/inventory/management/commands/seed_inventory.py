"""Management command to seed inventory data from the live catalog."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

import httpx
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.inventory.domain.enums import ReservationStatus, StockMovementType
from modules.inventory.infrastructure.models import (
    StockItemModel,
    StockMovementModel,
    StockReservationModel,
    WarehouseModel,
)


class Command(BaseCommand):
    """Seed inventory database with stock for the actual product catalog."""

    help = "Seed inventory database from product_service catalog for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing inventory data before seeding",
        )
        parser.add_argument(
            "--catalog-url",
            default=os.getenv("PRODUCT_SERVICE_URL", "http://product_service:8002"),
            help="Base URL for product_service",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing inventory data..."))
            StockMovementModel.objects.all().delete()
            StockReservationModel.objects.all().delete()
            StockItemModel.objects.all().delete()
            WarehouseModel.objects.all().delete()

        products = self._fetch_products(options["catalog_url"])
        if not products:
            raise CommandError("No products found in product_service. Seed product_service first.")

        warehouses = self._ensure_warehouses()
        self.stdout.write(self.style.SUCCESS(f"Using {len(products)} catalog products for inventory seed"))

        created_stock_items = 0
        created_movements = 0
        created_reservations = 0

        for index, product in enumerate(products):
            product_id = product.get("id")
            if not product_id:
                continue

            target_stock = int(product.get("stock") or product.get("attributes", {}).get("stock", 25) or 25)
            default_sku = product.get("default_sku") or f"{str(product.get('slug', 'SKU')).upper().replace('-', '')}-STD"

            for warehouse in warehouses:
                stock_item, created = StockItemModel.objects.get_or_create(
                    product_id=product_id,
                    variant_id=None,
                    warehouse_code=warehouse.code,
                    defaults={
                        "id": uuid.uuid4(),
                        "sku": default_sku,
                        "on_hand_quantity": target_stock,
                        "reserved_quantity": 0,
                        "safety_stock": max(3, min(10, target_stock // 4)),
                        "is_active": True,
                    },
                )

                changed_fields = []
                if stock_item.sku != default_sku:
                    stock_item.sku = default_sku
                    changed_fields.append("sku")
                if stock_item.on_hand_quantity != target_stock:
                    stock_item.on_hand_quantity = target_stock
                    changed_fields.append("on_hand_quantity")
                if not stock_item.is_active:
                    stock_item.is_active = True
                    changed_fields.append("is_active")
                if stock_item.safety_stock != max(3, min(10, target_stock // 4)):
                    stock_item.safety_stock = max(3, min(10, target_stock // 4))
                    changed_fields.append("safety_stock")
                if changed_fields:
                    changed_fields.append("updated_at")
                    stock_item.save(update_fields=changed_fields)

                if created:
                    created_stock_items += 1
                    StockMovementModel.objects.create(
                        id=uuid.uuid4(),
                        stock_item=stock_item,
                        product_id=stock_item.product_id,
                        variant_id=stock_item.variant_id,
                        movement_type=StockMovementType.STOCK_IN.value,
                        quantity=stock_item.on_hand_quantity,
                        reference_type="initial_stock",
                        reference_id=f"INIT-{stock_item.id}",
                        note="Initial stock created from live product catalog seed",
                        metadata={"seed": True, "product_name": product.get("name")},
                    )
                    created_movements += 1

            if index < 3:
                main_stock = StockItemModel.objects.filter(product_id=product_id, warehouse_code="MAIN").first()
                if main_stock and main_stock.available_quantity >= 2:
                    reservation, reservation_created = StockReservationModel.objects.get_or_create(
                        stock_item=main_stock,
                        product_id=main_stock.product_id,
                        variant_id=main_stock.variant_id,
                        order_id=uuid.uuid5(uuid.NAMESPACE_URL, f"seed-order:{product_id}"),
                        defaults={
                            "id": uuid.uuid4(),
                            "reservation_code": f"RES-{uuid.uuid4().hex[:8].upper()}",
                            "quantity": 2,
                            "status": ReservationStatus.ACTIVE.value,
                            "expires_at": timezone.now() + timedelta(hours=3),
                            "metadata": {"seed": True, "product_name": product.get("name")},
                        },
                    )
                    if reservation_created:
                        main_stock.reserved_quantity = min(main_stock.on_hand_quantity, main_stock.reserved_quantity + reservation.quantity)
                        main_stock.save(update_fields=["reserved_quantity", "updated_at"])
                        StockMovementModel.objects.create(
                            id=uuid.uuid4(),
                            stock_item=main_stock,
                            product_id=main_stock.product_id,
                            variant_id=main_stock.variant_id,
                            movement_type=StockMovementType.RESERVATION_CREATED.value,
                            quantity=reservation.quantity,
                            reference_type="order",
                            reference_id=str(reservation.order_id),
                            note="Sample reservation created from live catalog seed",
                            metadata={"seed": True, "product_name": product.get("name")},
                        )
                        created_reservations += 1
                        created_movements += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created_stock_items} stock items"))
        self.stdout.write(self.style.SUCCESS(f"Created {created_reservations} sample reservations"))
        self.stdout.write(self.style.SUCCESS(f"Created {created_movements} stock movements"))
        self.stdout.write(self.style.SUCCESS("Inventory seeding completed successfully"))

    def _ensure_warehouses(self):
        main_warehouse, _ = WarehouseModel.objects.get_or_create(
            code="MAIN",
            defaults={
                "name": "Main Warehouse",
                "warehouse_type": "main",
                "location": "Ho Chi Minh City",
                "is_active": True,
            },
        )
        branch_warehouse, _ = WarehouseModel.objects.get_or_create(
            code="BRANCH_01",
            defaults={
                "name": "Branch Warehouse 01",
                "warehouse_type": "branch",
                "location": "Da Nang",
                "is_active": True,
            },
        )
        return [main_warehouse, branch_warehouse]

    @staticmethod
    def _fetch_products(catalog_url: str):
        base_url = catalog_url.rstrip("/")
        candidates = [
            f"{base_url}/api/v1/catalog/products/",
            "http://product_service:8002/api/v1/catalog/products/",
            "http://host.docker.internal:8002/api/v1/catalog/products/",
            "http://localhost:8002/api/v1/catalog/products/",
        ]
        last_error = None
        for url in candidates:
            try:
                with httpx.Client(timeout=8.0) as client:
                    response = client.get(url, params={"page_size": 200})
                    response.raise_for_status()
                payload = response.json()
                results = payload.get("results", []) if isinstance(payload, dict) else []
                if results:
                    return results
            except Exception as exc:  # pragma: no cover - network fallback
                last_error = exc
        raise CommandError(f"Could not fetch live catalog from product_service: {last_error}")
