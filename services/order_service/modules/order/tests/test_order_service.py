"""
Comprehensive tests for Order service.

Tests cover domain logic, application services, and API endpoints.
"""

from decimal import Decimal
from uuid import uuid4
from datetime import datetime

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from ..domain import (
    Order, OrderItem, OrderStatus, PaymentStatus, FulfillmentStatus, Currency,
    OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, Money, OrderValidator, OrderCalculationService
)
from ..infrastructure import OrderRepositoryImpl, OrderItemRepositoryImpl
from ..infrastructure.models import OrderModel, OrderItemModel, OrderStatusHistoryModel
from ..application import (
    GetUserOrdersService, GetOrderDetailService, CreateOrderFromCartService
)


class OrderEntityTests(TestCase):
    """Test Order domain entity."""
    
    def setUp(self):
        self.order_id = uuid4()
        self.user_id = uuid4()
        self.customer = CustomerSnapshot(
            name="Test User",
            email="test@example.com",
            phone="0123456789",
            user_id=self.user_id,
        )
        self.address = AddressSnapshot(
            receiver_name="Receiver",
            receiver_phone="0987654321",
            line1="1 Main St",
            district="District 1",
            city="City",
            country="Vietnam",
        )
    
    def test_create_order_basic(self):
        """Test creating a basic order."""
        order = Order(
            id=self.order_id,
            order_number=OrderNumber("ORD-20260411-000001"),
            user_id=self.user_id,
            cart_id=uuid4(),
            currency=Currency.VND,
            customer_snapshot=self.customer,
            address_snapshot=self.address,
        )
        
        self.assertEqual(order.id, self.order_id)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment_status, PaymentStatus.UNPAID)
        self.assertEqual(order.fulfillment_status, FulfillmentStatus.UNFULFILLED)
    
    def test_add_order_item(self):
        """Test adding item to order."""
        order = Order(
            id=self.order_id,
            order_number=OrderNumber("ORD-20260411-000001"),
            user_id=self.user_id,
            cart_id=uuid4(),
            currency=Currency.VND,
            customer_snapshot=self.customer,
            address_snapshot=self.address,
        )
        
        item = OrderItem(
            id=uuid4(),
            order_id=order.id,
            product_reference=ProductReference(product_id=uuid4(), sku="SKU-1"),
            product_snapshot=ProductSnapshot(
                product_id=uuid4(),
                name="Test Product",
                slug="test-product",
            ),
            quantity=5,
            unit_price=Money(Decimal("100000"), Currency.VND),
            currency=Currency.VND,
        )
        
        order.add_item(item)
        
        self.assertEqual(len(order.items), 1)
        self.assertEqual(order.item_count, 1)
        self.assertEqual(order.total_quantity, 5)
    
    def test_mark_payment_success(self):
        """Test marking order as paid."""
        order = Order(
            id=self.order_id,
            order_number=OrderNumber("ORD-20260411-000001"),
            user_id=self.user_id,
            cart_id=uuid4(),
            currency=Currency.VND,
            customer_snapshot=self.customer,
            address_snapshot=self.address,
            status=OrderStatus.AWAITING_PAYMENT,
            payment_status=PaymentStatus.PENDING,
        )
        
        order.mark_payment_success()
        
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertEqual(order.payment_status, PaymentStatus.PAID)
        self.assertIsNotNone(order.paid_at)
    
    def test_invalid_state_transition_fails(self):
        """Test that invalid state transitions are rejected."""
        order = Order(
            id=self.order_id,
            order_number=OrderNumber("ORD-20260411-000001"),
            user_id=self.user_id,
            cart_id=uuid4(),
            currency=Currency.VND,
            customer_snapshot=self.customer,
            address_snapshot=self.address,
            status=OrderStatus.COMPLETED,
        )
        
        # Cannot mark as payment success from COMPLETED
        with self.assertRaises(ValueError):
            order.mark_payment_success()


class OrderValidatorTests(TestCase):
    """Test order validation logic."""
    
    def test_validate_checkout_payload_valid(self):
        """Test valid checkout payload."""
        payload = {
            "user_id": str(uuid4()),
            "cart_id": str(uuid4()),
            "items": [
                {
                    "product_id": str(uuid4()),
                    "quantity": 5,
                    "unit_price": "100000",
                }
            ],
            "customer": {
                "name": "Customer",
                "email": "test@example.com",
            },
            "shipping_address": {
                "receiver_name": "Receiver",
                "line1": "1 Main St",
                "district": "District",
            },
            "totals": {
                "subtotal": "500000",
                "grand_total": "550000",
            }
        }
        
        result = OrderValidator.validate_checkout_payload(payload)
        self.assertTrue(result)

    def test_validate_checkout_payload_without_customer_is_allowed(self):
        """Checkout payloads can omit customer and rely on user lookup."""
        payload = {
            "user_id": str(uuid4()),
            "cart_id": str(uuid4()),
            "items": [
                {
                    "product_id": str(uuid4()),
                    "quantity": 1,
                    "unit_price": "100000",
                }
            ],
            "shipping_address": {
                "receiver_name": "Receiver",
                "line1": "1 Main St",
                "district": "District",
            },
            "totals": {
                "subtotal": "100000",
                "grand_total": "100000",
            }
        }

        result = OrderValidator.validate_checkout_payload(payload)
        self.assertTrue(result)
    
    def test_validate_checkout_payload_missing_items(self):
        """Test validation rejects empty cart."""
        payload = {
            "user_id": str(uuid4()),
            "cart_id": str(uuid4()),
            "items": [],  # Empty!
            "customer": {"name": "Customer", "email": "test@example.com"},
            "shipping_address": {"receiver_name": "Receiver", "line1": "1 Main St", "district": "District"},
            "totals": {},
        }
        
        with self.assertRaises(ValueError):
            OrderValidator.validate_checkout_payload(payload)


class OrderCalculationServiceTests(TestCase):
    """Test order calculation logic."""
    
    def test_calculate_totals(self):
        """Test total calculation."""
        items = [
            OrderItem(
                id=uuid4(),
                order_id=uuid4(),
                product_reference=ProductReference(product_id=uuid4()),
                product_snapshot=ProductSnapshot(
                    product_id=uuid4(),
                    name="Product",
                    slug="product",
                ),
                quantity=2,
                unit_price=Money(Decimal("100000"), Currency.VND),
                currency=Currency.VND,
            ),
            OrderItem(
                id=uuid4(),
                order_id=uuid4(),
                product_reference=ProductReference(product_id=uuid4()),
                product_snapshot=ProductSnapshot(
                    product_id=uuid4(),
                    name="Product 2",
                    slug="product-2",
                ),
                quantity=3,
                unit_price=Money(Decimal("50000"), Currency.VND),
                currency=Currency.VND,
            ),
        ]
        
        totals = OrderCalculationService.calculate_order_totals(items)
        
        # 2 * 100000 + 3 * 50000 = 200000 + 150000 = 350000
        self.assertEqual(totals["subtotal"].amount, Decimal("350000"))
        self.assertEqual(totals["grand_total"].amount, Decimal("350000"))


class OrderRepositoryTests(TransactionTestCase):
    """Test repository persistence."""
    
    def setUp(self):
        self.repo = OrderRepositoryImpl()
        self.item_repo = OrderItemRepositoryImpl()
    
    def test_save_and_retrieve_order(self):
        """Test saving and retrieving order."""
        order = Order(
            id=uuid4(),
            order_number=OrderNumber("ORD-20260411-000001"),
            user_id=uuid4(),
            cart_id=uuid4(),
            currency=Currency.VND,
            customer_snapshot=CustomerSnapshot(
                name="Test",
                email="test@example.com",
            ),
            address_snapshot=AddressSnapshot(
                receiver_name="Receiver",
                receiver_phone="123",
                line1="Street",
                district="District",
                city="City",
            ),
        )
        
        # Save
        self.repo.save(order)
        
        # Retrieve
        retrieved = self.repo.get_by_id(order.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, order.id)
        self.assertEqual(retrieved.order_number.value, "ORD-20260411-000001")
    
    def test_get_user_orders(self):
        """Test retrieving user's orders."""
        user_id = uuid4()
        
        for i in range(3):
            order = Order(
                id=uuid4(),
                order_number=OrderNumber(f"ORD-20260411-00000{i}"),
                user_id=user_id,
                cart_id=uuid4(),
                currency=Currency.VND,
                customer_snapshot=CustomerSnapshot(name="Test", email="test@example.com"),
                address_snapshot=AddressSnapshot(
                    receiver_name="Receiver",
                    receiver_phone="123",
                    line1="Street",
                    district="District",
                    city="City",
                ),
            )
            self.repo.save(order)
        
        orders = self.repo.get_user_orders(user_id)
        
        self.assertEqual(len(orders), 3)
        self.assertTrue(all(o.user_id == user_id for o in orders))


class GetOrderDetailServiceTests(TestCase):
    """Test GetOrderDetail use case."""
    
    def test_get_nonexistent_order(self):
        """Test getting order that doesn't exist."""
        service = GetOrderDetailService()
        result = service.execute(uuid4())
        
        self.assertIsNone(result)


class CreateOrderFromCartServiceTests(TestCase):
    """Test order creation orchestration."""

    def test_build_order_uses_user_profile_when_cart_payload_has_no_customer(self):
        """Checkout payloads from cart should still create a customer snapshot."""

        class FakeUserClient:
            def get_user_by_id(self, user_id):
                return {
                    "id": str(user_id),
                    "email": "john@example.com",
                    "full_name": "John Doe",
                    "phone_number": "0909123456",
                }

        service = CreateOrderFromCartService(user_client=FakeUserClient())
        user_id = uuid4()
        order = service._build_order_from_payload(
            user_id=user_id,
            cart_id=uuid4(),
            checkout_payload={
                "items": [
                    {
                        "product_id": str(uuid4()),
                        "product_name": "Galaxy A55",
                        "product_slug": "galaxy-a55",
                        "quantity": 1,
                        "unit_price": "9990000",
                    }
                ]
            },
            shipping_address={
                "receiver_name": "John Doe",
                "receiver_phone": "0909123456",
                "line1": "1 Main St",
                "district": "District 1",
                "city": "Ho Chi Minh City",
            },
        )

        self.assertEqual(order.customer_snapshot.name, "John Doe")
        self.assertEqual(order.customer_snapshot.email, "john@example.com")
        self.assertEqual(order.customer_snapshot.phone, "0909123456")
        self.assertEqual(len(order.items), 1)


# Integration tests would require mocking inter-service clients
class OrderAPITests(TestCase):
    """Test Order API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.user_id = uuid4()
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success"], True)
    
    def test_list_orders_requires_auth(self):
        """Test that list orders requires authentication."""
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, 403)
    
    def test_list_orders_with_auth(self):
        """Test listing orders with auth."""
        self.client.defaults["HTTP_X_USER_ID"] = str(self.user_id)
        response = self.client.get("/api/v1/orders/")
        
        # Should succeed even if no orders
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success"], True)

class OrderRequestResponseTests:
    """Test request/response serialization."""
    
    def test_order_detail_serialization(self):
        """Test OrderDetailDTO serialization."""
        from ...application import OrderDetailDTO
        from ...presentation.serializers import OrderDetailSerializer
        
        order_dto = OrderDetailDTO(
            id=uuid4(),
            order_number="ORD-20260411-000001",
            user_id=uuid4(),
            status="pending",
            payment_status="unpaid",
            fulfillment_status="unfulfilled",
            items=[],
            totals=None,
            customer_name="Test",
            customer_email="test@example.com",
            customer_phone=None,
            shipping_address=None,
        )
        
        serializer = OrderDetailSerializer(order_dto)
        data = serializer.data
        
        self.assertEqual(data["order_number"], "ORD-20260411-000001")
        self.assertEqual(data["status"], "pending")
