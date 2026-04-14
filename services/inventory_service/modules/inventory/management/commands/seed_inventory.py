"""
Management command to seed inventory data.

Creates sample inventory for development and testing.
"""
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from modules.inventory.infrastructure.models import (
    StockItemModel,
    StockReservationModel,
    StockMovementModel,
    WarehouseModel,
)
from modules.inventory.domain.enums import StockMovementType, ReservationStatus


class Command(BaseCommand):
    """Seed inventory data command."""
    
    help = "Seed inventory database with sample data for development"
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )
    
    def handle(self, *args, **options):
        """Execute command."""
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            StockMovementModel.objects.all().delete()
            StockReservationModel.objects.all().delete()
            StockItemModel.objects.all().delete()
            WarehouseModel.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS("Seeding inventory data..."))
        
        # Create warehouses
        main_warehouse, _ = WarehouseModel.objects.get_or_create(
            code="MAIN",
            defaults={
                "name": "Main Warehouse",
                "warehouse_type": "main",
                "location": "New York, NY",
                "is_active": True,
            },
        )
        
        branch_warehouse, _ = WarehouseModel.objects.get_or_create(
            code="BRANCH_01",
            defaults={
                "name": "Branch Warehouse 01",
                "warehouse_type": "branch",
                "location": "Los Angeles, CA",
                "is_active": True,
            },
        )
        
        self.stdout.write(self.style.SUCCESS(f"✓ Created {2} warehouses"))
        
        # Product UUIDs (use real UUIDs that would come from product_service)
        products = [
            {
                "id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
                "name": "Samsung Galaxy S24",
                "variants": [
                    {
                        "id": uuid.UUID("22345678-1234-5678-1234-567812345678"),
                        "name": "256GB Black",
                        "sku": "SGS24-256-BLK",
                    },
                    {
                        "id": uuid.UUID("32345678-1234-5678-1234-567812345678"),
                        "name": "512GB White",
                        "sku": "SGS24-512-WHT",
                    },
                ],
            },
            {
                "id": uuid.UUID("43456789-2345-6789-2345-678923456789"),
                "name": "iPhone 15 Pro",
                "variants": [
                    {
                        "id": uuid.UUID("53456789-2345-6789-2345-678923456789"),
                        "name": "128GB Space Black",
                        "sku": "IP15P-128-SB",
                    },
                ],
            },
            {
                "id": uuid.UUID("64567890-3456-7890-3456-789034567890"),
                "name": "Sony WH-1000XM5 Headphones",
                "variants": None,
                "sku": "SONY-WH1000XM5",
            },
            {
                "id": uuid.UUID("75678901-4567-8901-4567-890145678901"),
                "name": "iPad Air 11-inch",
                "variants": [
                    {
                        "id": uuid.UUID("85678901-4567-8901-4567-890145678901"),
                        "name": "256GB Space Gray",
                        "sku": "IPAD-256-SG",
                    },
                ],
            },
            {
                "id": uuid.UUID("96789012-5678-9012-5678-901256789012"),
                "name": "MacBook Pro 14-inch",
                "variants": [
                    {
                        "id": uuid.UUID("a6789012-5678-9012-5678-901256789012"),
                        "name": "512GB M3",
                        "sku": "MBP14-512-M3",
                    },
                ],
            },
        ]
        
        stock_items = []
        movement_count = 0
        
        # Create stock items for each product/variant combo
        for product in products:
            if product.get("variants"):
                # Product with variants
                for variant in product["variants"]:
                    for warehouse in [main_warehouse, branch_warehouse]:
                        stock_item = StockItemModel.objects.create(
                            id=uuid.uuid4(),
                            product_id=product["id"],
                            variant_id=variant["id"],
                            sku=variant.get("sku"),
                            warehouse_code=warehouse.code,
                            on_hand_quantity=self._get_random_quantity(),
                            reserved_quantity=0,
                            safety_stock=10,
                            is_active=True,
                        )
                        stock_items.append(stock_item)
                        
                        # Create stock_in movement
                        StockMovementModel.objects.create(
                            id=uuid.uuid4(),
                            stock_item=stock_item,
                            product_id=product["id"],
                            variant_id=variant["id"],
                            movement_type=StockMovementType.STOCK_IN.value,
                            quantity=stock_item.on_hand_quantity,
                            reference_type="initial_stock",
                            reference_id=f"INIT-{stock_item.id}",
                            note="Initial stock on seeding",
                        )
                        movement_count += 1
            else:
                # Product without variants
                for warehouse in [main_warehouse, branch_warehouse]:
                    stock_item = StockItemModel.objects.create(
                        id=uuid.uuid4(),
                        product_id=product["id"],
                        variant_id=None,
                        sku=product.get("sku"),
                        warehouse_code=warehouse.code,
                        on_hand_quantity=self._get_random_quantity(),
                        reserved_quantity=0,
                        safety_stock=10,
                        is_active=True,
                    )
                    stock_items.append(stock_item)
                    
                    # Create stock_in movement
                    StockMovementModel.objects.create(
                        id=uuid.uuid4(),
                        stock_item=stock_item,
                        product_id=product["id"],
                        variant_id=None,
                        movement_type=StockMovementType.STOCK_IN.value,
                        quantity=stock_item.on_hand_quantity,
                        reference_type="initial_stock",
                        reference_id=f"INIT-{stock_item.id}",
                        note="Initial stock on seeding",
                    )
                    movement_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(stock_items)} stock items"))
        
        # Create some sample reservations
        reservation_count = 0
        for stock_item in stock_items[:3]:  # Only first 3
            if stock_item.available_quantity >= 2:
                reservation = StockReservationModel.objects.create(
                    id=uuid.uuid4(),
                    reservation_code=f"RES-{uuid.uuid4().hex[:8].upper()}",
                    stock_item=stock_item,
                    product_id=stock_item.product_id,
                    variant_id=stock_item.variant_id,
                    order_id=uuid.uuid4(),
                    quantity=2,
                    status=ReservationStatus.ACTIVE.value,
                    expires_at=timezone.now() + timedelta(hours=1),
                )
                
                # Update stock item reserved quantity
                stock_item.reserved_quantity += 2
                stock_item.save(update_fields=["reserved_quantity"])
                
                # Create reservation movement
                StockMovementModel.objects.create(
                    id=uuid.uuid4(),
                    stock_item=stock_item,
                    product_id=stock_item.product_id,
                    variant_id=stock_item.variant_id,
                    movement_type=StockMovementType.RESERVATION_CREATED.value,
                    quantity=2,
                    reference_type="order",
                    reference_id=str(reservation.order_id),
                    note=f"Sample reservation {reservation.reservation_code}",
                )
                movement_count += 1
                reservation_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"✓ Created {reservation_count} sample reservations"))
        self.stdout.write(self.style.SUCCESS(f"✓ Created {movement_count} stock movements"))
        
        self.stdout.write(
            self.style.SUCCESS(
                "✓ Inventory seeding completed successfully!"
            )
        )
    
    @staticmethod
    def _get_random_quantity():
        """Get random quantity for seeding."""
        import random
        return random.randint(5, 100)
