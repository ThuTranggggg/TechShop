"""
Application Layer Tests

Tests for use case services and orchestration logic.
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta
import uuid

from modules.shipping.domain.entities import ShipmentStatus
from modules.shipping.application.services import (
    CreateShipmentService,
    GetShipmentDetailService,
    GetShipmentByReferenceService,
    GetShipmentStatusService,
    MarkPickedUpService,
    MarkInTransitService,
    MarkDeliveredService,
    CancelShipmentService,
)
from modules.shipping.application.dtos import CreateShipmentRequestDTO
from modules.shipping.infrastructure.models import ShipmentModel, ShipmentItemModel


class CreateShipmentServiceTest(TransactionTestCase):
    """Tests for CreateShipmentService"""
    
    def test_create_shipment_success(self):
        """Test successful shipment creation"""
        service = CreateShipmentService()
        
        req_dto = CreateShipmentRequestDTO(
            order_id="order-123",
            order_number="ORD-001",
            user_id="user-456",
            receiver_name="John Doe",
            receiver_phone="0912345678",
            address_line1="123 Main St",
            address_line2="",
            ward="Ward 1",
            district="District 1",
            city="Ho Chi Minh",
            country="VN",
            postal_code="70000",
            items=[
                {
                    "product_id": "prod-001",
                    "product_name": "Product A",
                    "sku": "SKU-001",
                    "quantity": 2,
                    "unit_price": 100000,
                    "total_price": 200000,
                }
            ],
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
        
        success, error, shipment_dto = service.execute(req_dto)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.order_id, "order-123")
        self.assertEqual(shipment_dto.status, ShipmentStatus.CREATED.value)
        
        # Verify database
        shipment = ShipmentModel.objects.get(id=shipment_dto.id)
        self.assertEqual(shipment.status, ShipmentStatus.CREATED.value)
        self.assertEqual(shipment.shipment_reference, shipment_dto.shipment_reference)
    
    def test_create_shipment_validation_failure(self):
        """Test shipment creation with invalid data"""
        service = CreateShipmentService()
        
        req_dto = CreateShipmentRequestDTO(
            order_id="",  # Invalid: empty order_id
            order_number="ORD-001",
            user_id="user-456",
            receiver_name="",  # Invalid: empty receiver_name
            receiver_phone="0912345678",
            address_line1="123 Main St",
            address_line2="",
            ward="Ward 1",
            district="District 1",
            city="Ho Chi Minh",
            country="VN",
            postal_code="70000",
            items=[],  # Invalid: empty items
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
        
        success, error, shipment_dto = service.execute(req_dto)
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIsNone(shipment_dto)


class GetShipmentDetailServiceTest(TestCase):
    """Tests for GetShipmentDetailService"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_get_shipment_detail_success(self):
        """Test retrieving shipment detail"""
        service = GetShipmentDetailService()
        
        shipment_dto = service.execute(str(self.shipment.id))
        
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.shipment_reference, "SHIP-001")
        self.assertEqual(shipment_dto.order_id, "order-123")
    
    def test_get_shipment_detail_not_found(self):
        """Test retrieving non-existent shipment"""
        service = GetShipmentDetailService()
        
        shipment_dto = service.execute(str(uuid.uuid4()))
        
        self.assertIsNone(shipment_dto)


class GetShipmentByReferenceServiceTest(TestCase):
    """Tests for GetShipmentByReferenceService"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-REF-123",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_get_shipment_by_reference_success(self):
        """Test retrieving shipment by reference"""
        service = GetShipmentByReferenceService()
        
        shipment_dto = service.execute("SHIP-REF-123")
        
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.shipment_reference, "SHIP-REF-123")
    
    def test_get_shipment_by_reference_not_found(self):
        """Test retrieving non-existent shipment by reference"""
        service = GetShipmentByReferenceService()
        
        shipment_dto = service.execute("NONEXISTENT-REF")
        
        self.assertIsNone(shipment_dto)


class ShipmentStatusTransitionTest(TransactionTestCase):
    """Tests for shipment status transitions"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-STATUS-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_mark_picked_up(self):
        """Test marking shipment as picked up"""
        service = MarkPickedUpService()
        
        success, error, shipment_dto = service.execute("SHIP-STATUS-001")
        
        self.assertTrue(success)
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.status, ShipmentStatus.PICKED_UP.value)
        
        # Verify database
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, ShipmentStatus.PICKED_UP.value)
    
    def test_mark_in_transit(self):
        """Test marking shipment as in transit"""
        # First mark as picked up
        self.shipment.status = ShipmentStatus.PICKED_UP.value
        self.shipment.save()
        
        service = MarkInTransitService()
        
        success, error, shipment_dto = service.execute("SHIP-STATUS-001")
        
        self.assertTrue(success)
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.status, ShipmentStatus.IN_TRANSIT.value)
    
    def test_mark_delivered(self):
        """Test marking shipment as delivered"""
        # Mark through all required states
        self.shipment.status = ShipmentStatus.OUT_FOR_DELIVERY.value
        self.shipment.save()
        
        service = MarkDeliveredService()
        
        success, error, shipment_dto = service.execute("SHIP-STATUS-001")
        
        self.assertTrue(success)
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.status, ShipmentStatus.DELIVERED.value)
        self.assertIsNotNone(shipment_dto.actual_delivery_date)


class ShipmentIdempotencyTest(TransactionTestCase):
    """Tests for idempotent operations"""
    
    def setUp(self):
        """Create delivered shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-IDEMPOTENT-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.DELIVERED.value,
            actual_delivery_date=timezone.now(),
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_mark_delivered_idempotent(self):
        """Test marking delivered shipment as delivered again (idempotency)"""
        service = MarkDeliveredService()
        
        # First call
        success1, error1, dto1 = service.execute("SHIP-IDEMPOTENT-001")
        self.assertTrue(success1)
        original_date = dto1.actual_delivery_date
        
        # Second call (idempotent)
        success2, error2, dto2 = service.execute("SHIP-IDEMPOTENT-001")
        self.assertTrue(success2)
        self.assertEqual(dto2.actual_delivery_date, original_date)
        
        # Verify no duplicate events created
        from modules.shipping.infrastructure.models import ShipmentTrackingEventModel
        events = ShipmentTrackingEventModel.objects.filter(shipment=self.shipment)
        # Should have same number of events after second call
        self.assertLessEqual(events.count(), 2)  # At most initial creation + one delivered event


class CancelShipmentServiceTest(TransactionTestCase):
    """Tests for CancelShipmentService"""
    
    def setUp(self):
        """Create test shipment"""
        self.shipment = ShipmentModel.objects.create(
            shipment_reference="SHIP-CANCEL-001",
            order_id="order-123",
            user_id="user-456",
            tracking_number="TRACK-001",
            status=ShipmentStatus.CREATED.value,
            receiver_address={"name": "John", "street": "123 Main"},
            total_items=1,
            total_weight=1.5,
            total_price=200000,
            service_level="standard",
            provider="mock",
            shipping_fee_amount=50000,
            currency="VND",
        )
    
    def test_cancel_created_shipment(self):
        """Test canceling a created shipment"""
        service = CancelShipmentService()
        
        success, error, shipment_dto = service.execute("SHIP-CANCEL-001")
        
        self.assertTrue(success)
        self.assertIsNotNone(shipment_dto)
        self.assertEqual(shipment_dto.status, ShipmentStatus.CANCELLED.value)
    
    def test_cancel_delivered_shipment_fails(self):
        """Test that canceling a delivered shipment fails"""
        self.shipment.status = ShipmentStatus.DELIVERED.value
        self.shipment.save()
        
        service = CancelShipmentService()
        
        success, error, shipment_dto = service.execute("SHIP-CANCEL-001")
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
