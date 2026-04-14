"""
Management command to seed demo orders.
"""

from django.core.management.base import BaseCommand
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta

from ..domain import (
    Order, OrderItem, OrderStatus, PaymentStatus, FulfillmentStatus, Currency,
    OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, Money
)
from ...infrastructure import OrderRepositoryImpl, OrderItemRepositoryImpl
from ...infrastructure.models import OrderStatusHistoryModel


class Command(BaseCommand):
    help = "Seed demo orders for testing"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of demo orders to create",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all existing orders before seeding",
        )
    
    def handle(self, *args, **options):
        count = options["count"]
        clean = options["clean"]
        
        if clean:
            self.stdout.write("Deleting all existing orders...")
            OrderStatusHistoryModel.objects.all().delete()
            from ...infrastructure.models import OrderModel, OrderItemModel
            OrderItemModel.objects.all().delete()
            OrderModel.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ All orders deleted"))
        
        self.stdout.write(f"Creating {count} demo orders...")
        
        repo = OrderRepositoryImpl()
        item_repo = OrderItemRepositoryImpl()
        
        statuses = [
            (OrderStatus.AWAITING_PAYMENT, PaymentStatus.PENDING, FulfillmentStatus.UNFULFILLED),
            (OrderStatus.PAID, PaymentStatus.PAID, FulfillmentStatus.PREPARING),
            (OrderStatus.PROCESSING, PaymentStatus.PAID, FulfillmentStatus.PREPARING),
            (OrderStatus.SHIPPING, PaymentStatus.PAID, FulfillmentStatus.SHIPPED),
            (OrderStatus.DELIVERED, PaymentStatus.PAID, FulfillmentStatus.DELIVERED),
            (OrderStatus.COMPLETED, PaymentStatus.PAID, FulfillmentStatus.DELIVERED),
            (OrderStatus.PAYMENT_FAILED, PaymentStatus.FAILED, FulfillmentStatus.UNFULFILLED),
            (OrderStatus.CANCELLED, PaymentStatus.UNPAID, FulfillmentStatus.CANCELLED),
        ]
        
        for i in range(count):
            order_num = i + 1
            status_idx = order_num % len(statuses)
            order_status, payment_status, fulfillment_status = statuses[status_idx]
            
            customer = CustomerSnapshot(
                name=f"Customer {order_num}",
                email=f"customer{order_num}@example.com",
                phone="0123456789",
                user_id=uuid4(),
            )
            
            address = AddressSnapshot(
                receiver_name=f"Receiver {order_num}",
                receiver_phone="0987654321",
                line1=f"{order_num} Main Street",
                line2="Apt 101",
                ward="Ward 1",
                district="District 1",
                city="Ho Chi Minh City",
                country="Vietnam",
                postal_code="70000",
            )
            
            order = Order(
                id=uuid4(),
                order_number=OrderNumber(f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(order_num).zfill(6)}"),
                user_id=customer.user_id,
                cart_id=uuid4(),
                currency=Currency.VND,
                customer_snapshot=customer,
                address_snapshot=address,
                status=order_status,
                payment_status=payment_status,
                fulfillment_status=fulfillment_status,
            )
            
            # Add sample items
            for j in range(1, 3):
                item = OrderItem(
                    id=uuid4(),
                    order_id=order.id,
                    product_reference=ProductReference(
                        product_id=uuid4(),
                        sku=f"SKU-{order_num}-{j}",
                    ),
                    product_snapshot=ProductSnapshot(
                        product_id=uuid4(),
                        name=f"Sample Product {j}",
                        slug=f"sample-product-{j}",
                        brand_name="Demo Brand",
                        category_name="Demo Category",
                    ),
                    quantity=j + 1,
                    unit_price=Money(Decimal("100000"), Currency.VND),
                    currency=Currency.VND,
                )
                order.add_item(item)
            
            # Set totals
            grand_total = sum(Decimal(str(item.line_total.amount)) for item in order.items)
            order.set_totals(
                subtotal=Money(grand_total, Currency.VND),
                shipping_fee=Money(Decimal("50000"), Currency.VND),
                discount=Money(Decimal("0"), Currency.VND),
                tax=Money(Decimal("0"), Currency.VND),
                grand_total=Money(grand_total + Decimal("50000"), Currency.VND),
            )
            
            # Set milestones based on status
            if order_status in [OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPING, OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
                order.placed_at = datetime.utcnow() - timedelta(days=order_num)
                order.paid_at = datetime.utcnow() - timedelta(days=order_num - 1)
            elif order_status == OrderStatus.CANCELLED:
                order.placed_at = datetime.utcnow() - timedelta(days=order_num)
                order.cancelled_at = datetime.utcnow() - timedelta(days=order_num - 1)
            
            # Save order
            repo.save(order)
            
            # Save items
            for item in order.items:
                item_repo.save(item)
            
            # Record status history
            OrderStatusHistoryModel.objects.create(
                order_id=order.id,
                from_status=None,
                to_status=order_status.value,
                note=f"Demo order {order_num} created",
                metadata={"demo": True},
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ Order {order.order_number} ({order_status.value}) created")
            )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Successfully created {count} demo orders")
        )
