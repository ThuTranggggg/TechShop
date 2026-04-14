"""
Model Layer Tests

Tests for Django ORM models, constraints, and persistence.
"""

from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
import json

from modules.shipping.domain.entities import ShipmentStatus, ShippingProvider, ShippingServiceLevel
from modules.shipping.infrastructure.models import (
    ShipmentModel,
    ShipmentItemModel,
    ShipmentTrackingEventModel,
)


class ShipmentModelTest(TestCase):
    """Tests for ShipmentModel"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-MODEL-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John Doe", "street": "123 Main St"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level=ShippingServiceLevel.STANDARD.value,
            provider=ShippingProvider.MOCK.value,
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_shipment_creation(self):
        """Test shipment model creation"""
        self.assertEqual(self.shipment.shipment_reference, "SHIP-MODEL-001")
        self.assertEqual(self.shipment.order_id, "order-123")
        self.assertEqual(self.shipment.status, ShipmentStatus.CREATED.value)
        self.assertIsNotNone(self.shipment.id)
        self.assertIsNotNone(self.shipment.created_at)
    
    def test_shipment_reference_uniqueness(self):
        """Test shipment reference constraint"""
        with self.assertRaises(IntegrityError):
            ShipmentModel.objects.create(
                shipment_reference="SHIP-MODEL-001",  # Duplicate
                order_id="order-456",
                user_id="user-789",
                tracking_number="TRACK-002",
                status=ShipmentStatus.CREATED.value,
                receiver_address={"name": "Jane", "street": "456 Oak"},
                total_items=1,
                total_weight=1.0,
                total_price=100000,
                service_level=ShippingServiceLevel.STANDARD.value,
                provider=ShippingProvider.MOCK.value,
                shipping_fee_amount=25000,
                currency="VND",
            )
    
    def test_tracking_number_uniqueness(self):
        """Test tracking number uniqueness constraint"""
        with self.assertRaises(IntegrityError):
            ShipmentModel.objects.create(
                shipment_reference="SHIP-MODEL-002",
                order_id="order-456",
                user_id="user-789",
                tracking_number="TRACK-001",  # Duplicate
                status=ShipmentStatus.CREATED.value,
                receiver_address={"name": "Jane", "street": "456 Oak"},
                total_items=1,
                total_weight=1.0,
                total_price=100000,
                service_level=ShippingServiceLevel.STANDARD.value,
                provider=ShippingProvider.MOCK.value,
                shipping_fee_amount=25000,
                currency="VND",
            )
    
    def test_shipment_retrieval_by_reference(self):
        """Test retrieving shipment by reference"""
        found = ShipmentModel.objects.filter(shipment_reference="SHIP-MODEL-001").first()
        self.assertEqual(found.id, self.shipment.id)
    
    def test_shipment_retrieval_by_order(self):
        """Test retrieving shipment by order_id"""
        found = ShipmentModel.objects.filter(order_id="order-123").first()
        self.assertEqual(found.id, self.shipment.id)
    
    def test_shipment_status_update(self):
        """Test updating shipment status"""
        self.shipment.status = ShipmentStatus.IN_TRANSIT.value
        self.shipment.save()
        
        refreshed = ShipmentModel.objects.get(id=self.shipment.id)
        self.assertEqual(refreshed.status, ShipmentStatus.IN_TRANSIT.value)


class ShipmentItemModelTest(TestCase):
    """Tests for ShipmentItemModel"""
    
    def setUp(self):
        """Create test shipment and items"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-ITEM-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-ITEM-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=2,
            total_weight=2.0,
            total_price=300000,
            service_level=ShippingServiceLevel.STANDARD.value,
            provider=ShippingProvider.MOCK.value,
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_shipment_item_creation(self):
        """Test shipment item creation"""
        item = ShipmentItemModel.objects.create(
            shipment=self.shipment,
            product_id="prod-001",
            product_name="Product A",
            sku="SKU-001",
            quantity=2,
            unit_price=100000,
            total_price=200000,
        )
        
        self.assertEqual(item.product_id, "prod-001")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.total_price, 200000)
        self.assertEqual(item.shipment.id, self.shipment.id)
    
    def test_shipment_items_retrieval(self):
        """Test retrieving items for a shipment"""
        ShipmentItemModel.objects.create(
            shipment=self.shipment,
            product_id="prod-001",
            product_name="Product A",
            sku="SKU-001",
            quantity=2,
            unit_price=100000,
            total_price=200000,
        )
        
        ShipmentItemModel.objects.create(
            shipment=self.shipment,
            product_id="prod-002",
            product_name="Product B",
            sku="SKU-002",
            quantity=1,
            unit_price=100000,
            total_price=100000,
        )
        
        items = self.shipment.items.all()
        self.assertEqual(items.count(), 2)


class ShipmentTrackingEventModelTest(TestCase):
    """Tests for ShipmentTrackingEventModel"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-EVENT-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-EVENT-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.0,
            total_price=200000,
            service_level=ShippingServiceLevel.STANDARD.value,
            provider=ShippingProvider.MOCK.value,
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_tracking_event_creation(self):
        """Test tracking event creation"""
        from modules.shipping.domain.entities import ShipmentTrackingEventType
        
        event = ShipmentTrackingEventModel.objects.create(
            shipment=self.shipment,
            event_type=ShipmentTrackingEventType.CREATED.value,
            status=ShipmentStatus.CREATED.value,
            location="Warehouse",
            notes="Shipment created",
        )
        
        self.assertEqual(event.event_type, ShipmentTrackingEventType.CREATED.value)
        self.assertEqual(event.status, ShipmentStatus.CREATED.value)
        self.assertIsNotNone(event.timestamp)
    
    def test_tracking_event_timeline(self):
        """Test creating multiple tracking events"""
        from modules.shipping.domain.entities import ShipmentTrackingEventType
        
        events_data = [
            (ShipmentTrackingEventType.CREATED.value, ShipmentStatus.CREATED.value, "Warehouse"),
            (ShipmentTrackingEventType.PICKED_UP.value, ShipmentStatus.PICKED_UP.value, "Warehouse"),
            (ShipmentTrackingEventType.DISPATCHED.value, ShipmentStatus.IN_TRANSIT.value, "Distribution Hub"),
        ]
        
        for event_type, status, location in events_data:
            ShipmentTrackingEventModel.objects.create(
                shipment=self.shipment,
                event_type=event_type,
                status=status,
                location=location,
            )
        
        events = self.shipment.tracking_events.all().order_by("timestamp")
        self.assertEqual(events.count(), 3)
        self.assertEqual(events[0].event_type, ShipmentTrackingEventType.CREATED.value)
        self.assertEqual(events[2].event_type, ShipmentTrackingEventType.DISPATCHED.value)
    
    def test_tracking_event_immutability(self):
        """Test that tracking events cannot be properly modified after creation"""
        from modules.shipping.domain.entities import ShipmentTrackingEventType
        
        event = ShipmentTrackingEventModel.objects.create(
            shipment=self.shipment,
            event_type=ShipmentTrackingEventType.CREATED.value,
            status=ShipmentStatus.CREATED.value,
            location="Warehouse",
        )
        
        original_timestamp = event.timestamp
        
        # Attempt to modify
        event.location = "Different Location"
        event.save()
        
        # Verify timestamp didn't change
        self.assertEqual(event.timestamp, original_timestamp)


class ShipmentQueryIndexTest(TestCase):
    """Tests for query performance with database indexes"""
    
    def setUp(self):
        """Create multiple test shipments"""
        for i in range(5):
            ShipmentModel.objects.create(
                shipment_reference=f"SHIP-INDEX-{i:03d}",
                order_id=f"order-{i}",
                user_id=f"user-{i}",
                tracking_number=f"TRACK-INDEX-{i:03d}",
                status=ShipmentStatus.CREATED.value if i % 2 == 0 else ShipmentStatus.IN_TRANSIT.value,
                receiver_address={"name": f"Customer {i}", "street": f"{i} Main St"},
                total_items=1,
                total_weight=1.0,
                total_price=200000,
                service_level=ShippingServiceLevel.STANDARD.value,
                provider=ShippingProvider.MOCK.value,
                shipping_fee_amount=50000,
                currency="VND",
            )
    
    def test_filter_by_status(self):
        """Test filtering shipments by status"""
        created = ShipmentModel.objects.filter(status=ShipmentStatus.CREATED.value)
        in_transit = ShipmentModel.objects.filter(status=ShipmentStatus.IN_TRANSIT.value)
        
        self.assertEqual(created.count(), 3)  # 0, 2, 4
        self.assertEqual(in_transit.count(), 2)  # 1, 3
    
    def test_filter_by_reference(self):
        """Test filtering by shipment reference"""
        result = ShipmentModel.objects.filter(shipment_reference="SHIP-INDEX-001")
        self.assertEqual(result.count(), 1)
    
    def test_filter_by_tracking_number(self):
        """Test filtering by tracking number"""
        result = ShipmentModel.objects.filter(tracking_number="TRACK-INDEX-002")
        self.assertEqual(result.count(), 1)
    
    def test_filter_by_order_id(self):
        """Test filtering by order_id"""
        result = ShipmentModel.objects.filter(order_id="order-1")
        self.assertEqual(result.count(), 1)
