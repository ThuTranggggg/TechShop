"""
Management command to seed cart data for development.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from uuid import uuid4
from decimal import Decimal

from modules.cart.infrastructure.models import CartModel, CartItemModel
from modules.cart.domain.enums import CartStatus, CartItemStatus


class Command(BaseCommand):
    help = "Seed cart service with demo data"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing carts before seeding',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_data()
        
        self.seed_carts()
        self.stdout.write(
            self.style.SUCCESS("✓ Cart seeding completed successfully")
        )
    
    def clear_existing_data(self):
        """Clear existing cart data."""
        count_items, _ = CartItemModel.objects.all().delete()
        count_carts, _ = CartModel.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(
                f"Cleared {count_carts} carts and {count_items} items"
            )
        )
    
    def seed_carts(self):
        """Seed demo carts."""
        self.stdout.write("Seeding carts...")
        
        # Demo user IDs (assuming product_service has created these)
        user_ids = [
            "550e8400-e29b-41d4-a716-446655440000",  # User 1
            "550e8400-e29b-41d4-a716-446655440001",  # User 2
        ]
        
        product_variants = [
            {
                "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "variant_id": None,
                "product_name": "Samsung Galaxy S24",
                "product_slug": "samsung-galaxy-s24",
                "sku": "SKU-S24-001",
                "brand_name": "Samsung",
                "category_name": "Smartphones",
                "thumbnail_url": "https://example.com/phone.jpg",
                "price": Decimal("999.99"),
                "quantity": 2,
            },
            {
                "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d480",
                "variant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d481",
                "product_name": "iPhone 15 Pro",
                "variant_name": "256GB Black",
                "product_slug": "iphone-15-pro",
                "sku": "SKU-IP15P-256",
                "brand_name": "Apple",
                "category_name": "Smartphones",
                "thumbnail_url": "https://example.com/iphone.jpg",
                "price": Decimal("1099.99"),
                "quantity": 1,
            },
            {
                "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d482",
                "variant_id": None,
                "product_name": "Sony WH-1000XM5 Headphones",
                "product_slug": "sony-wh-1000xm5",
                "sku": "SKU-SONY-XM5",
                "brand_name": "Sony",
                "category_name": "Audio",
                "thumbnail_url": "https://example.com/headphones.jpg",
                "price": Decimal("379.99"),
                "quantity": 1,
            },
        ]
        
        for user_id in user_ids:
            # Create active cart
            cart = CartModel.objects.create(
                id=uuid4(),
                user_id=user_id,
                status=CartStatus.ACTIVE.value,
                currency="USD",
                subtotal_amount=Decimal("0.00"),
                total_quantity=0,
                item_count=0,
            )
            
            self.stdout.write(
                f"  Created cart {cart.id} for user {user_id}"
            )
            
            # Add items to cart
            total_amount = Decimal("0.00")
            total_qty = 0
            
            for product in product_variants[:2]:  # Add first 2 products
                item = CartItemModel.objects.create(
                    id=uuid4(),
                    cart=cart,
                    product_id=product["product_id"],
                    variant_id=product["variant_id"],
                    product_name_snapshot=product["product_name"],
                    product_slug_snapshot=product["product_slug"],
                    variant_name_snapshot=product.get("variant_name"),
                    brand_name_snapshot=product["brand_name"],
                    category_name_snapshot=product["category_name"],
                    sku=product["sku"],
                    thumbnail_url_snapshot=product["thumbnail_url"],
                    quantity=product["quantity"],
                    unit_price_snapshot=product["price"],
                    currency="USD",
                    status=CartItemStatus.AVAILABLE.value,
                    attributes_snapshot={},
                )
                
                line_total = product["price"] *product["quantity"]
                total_amount += line_total
                total_qty += product["quantity"]
                
                self.stdout.write(
                    f"    Added item: {product['product_name']} (qty: {product['quantity']})"
                )
            
            # Update cart totals
            cart.subtotal_amount = total_amount
            cart.total_quantity = total_qty
            cart.item_count = CartItemModel.objects.filter(cart=cart).count()
            cart.save()
        
        self.stdout.write(f"  Seeded {len(user_ids)} carts with items")
