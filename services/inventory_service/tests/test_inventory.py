"""
Comprehensive tests for Inventory service.

Tests domain, application, and API layers.
"""
import uuid
import pytest
from django.test import TestCase
from datetime import datetime, timedelta
from django.utils import timezone

from modules.inventory.domain.entities import StockItem, StockReservation, StockMovement
from modules.inventory.domain.value_objects import ProductReference, StockStatus, Quantity
from modules.inventory.domain.enums import ReservationStatus, StockMovementType
from modules.inventory.domain.services import InventoryDomainService
from modules.inventory.infrastructure.models import (
    StockItemModel,
    StockReservationModel,
    StockMovementModel,
)


# ===================== Domain Tests =====================

class QuantityValueObjectTests(TestCase):
    """Tests for Quantity value object."""
    
    def test_quantity_cannot_be_negative(self):
        """Quantity should reject negative values."""
        with self.assertRaises(ValueError):
            Quantity(-1)
    
    def test_quantity_arithmetic(self):
        """Test quantity arithmetic operations."""
        q1 = Quantity(10)
        q2 = Quantity(5)
        
        q3 = q1 + q2
        self.assertEqual(q3.value, 15)
        
        q4 = q1 - q2
        self.assertEqual(q4.value, 5)
    
    def test_quantity_comparison(self):
        """Test quantity comparison."""
        q1 = Quantity(10)
        q2 = Quantity(5)
        
        self.assertTrue(q1 > q2)
        self.assertFalse(q1 < q2)
        self.assertTrue(q1 >= q2)


class StockStatusValueObjectTests(TestCase):
    """Tests for StockStatus value object."""
    
    def test_available_quantity_calculation(self):
        """Available quantity should be on_hand - reserved."""
        status = StockStatus(on_hand_quantity=100, reserved_quantity=30)
        self.assertEqual(status.available_quantity, 70)
    
    def test_cannot_create_status_with_invalid_reserved(self):
        """Reserved cannot exceed on_hand."""
        with self.assertRaises(ValueError):
            StockStatus(on_hand_quantity=100, reserved_quantity=150)
    
    def test_can_reserve(self):
        """Test reservation checking."""
        status = StockStatus(on_hand_quantity=100, reserved_quantity=30)
        
        self.assertTrue(status.can_reserve(50))  # 50 < 70 available
        self.assertFalse(status.can_reserve(80))  # 80 > 70 available
    
    def test_reserve_creates_new_status(self):
        """Reserve should create new status."""
        status = StockStatus(on_hand_quantity=100, reserved_quantity=30)
        new_status = status.reserve(20)
        
        self.assertEqual(new_status.reserved_quantity, 50)
        self.assertEqual(new_status.available_quantity, 50)
    
    def test_release_reservation(self):
        """Release should reduce reserved quantity."""
        status = StockStatus(on_hand_quantity=100, reserved_quantity=50)
        new_status = status.release_reservation(20)
        
        self.assertEqual(new_status.reserved_quantity, 30)
    
    def test_confirm_reservation(self):
        """Confirm should deduct from both on_hand and reserved."""
        status = StockStatus(on_hand_quantity=100, reserved_quantity=50)
        new_status = status.confirm_reservation(30)
        
        self.assertEqual(new_status.on_hand_quantity, 70)
        self.assertEqual(new_status.reserved_quantity, 20)


class StockItemAggregateTests(TestCase):
    """Tests for StockItem aggregate root."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.product_ref = ProductReference(
            product_id=str(uuid.uuid4()),
            variant_id=str(uuid.uuid4()),
            sku="TEST-SKU-001",
        )
    
    def test_create_stock_item(self):
        """Should create stock item with correct state."""
        item = StockItem(
            id=uuid.uuid4(),
            product_reference=self.product_ref,
            warehouse_code="MAIN",
            on_hand_quantity=100,
            reserved_quantity=0,
            safety_stock=10,
        )
        
        self.assertEqual(item.on_hand_quantity, 100)
        self.assertEqual(item.available_quantity, 100)
        self.assertTrue(item.is_in_stock())
    
    def test_receive_stock(self):
        """Stock in should increase on_hand."""
        item = StockItem(
            id=uuid.uuid4(),
            product_reference=self.product_ref,
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
        
        item.receive_stock(50)
        self.assertEqual(item.on_hand_quantity, 150)
    
    def test_cannot_receive_negative_stock(self):
        """Cannot receive negative quantity."""
        item = StockItem(
            id=uuid.uuid4(),
            product_reference=self.product_ref,
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
        
        with self.assertRaises(ValueError):
            item.receive_stock(-10)
    
    def test_create_reservation(self):
        """Should create reservation and update item."""
        item = StockItem(
            id=uuid.uuid4(),
            product_reference=self.product_ref,
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
        
        reservation = item.create_reservation(30)
        
        self.assertEqual(item.reserved_quantity, 30)
        self.assertEqual(item.available_quantity, 70)
        self.assertEqual(reservation.status, ReservationStatus.ACTIVE)
    
    def test_cannot_over_reserve(self):
        """Cannot reserve more than available."""
        item = StockItem(
            id=uuid.uuid4(),
            product_reference=self.product_ref,
            warehouse_code="MAIN",
            on_hand_quantity=50,
            reserved_quantity=30,
        )
        
        with self.assertRaises(ValueError):
            item.create_reservation(30)  # Only 20 available


class StockReservationEntityTests(TestCase):
    """Tests for StockReservation entity."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.product_ref = ProductReference(
            product_id=str(uuid.uuid4()),
        )
    
    def test_create_reservation(self):
        """Should create active reservation."""
        res = StockReservation(
            id=uuid.uuid4(),
            stock_item_id=uuid.uuid4(),
            product_reference=self.product_ref,
            quantity=10,
        )
        
        self.assertEqual(res.status, ReservationStatus.ACTIVE)
        self.assertTrue(res.is_active())
    
    def test_reservation_expiry(self):
        """Reservation should track expiry."""
        res = StockReservation(
            id=uuid.uuid4(),
            stock_item_id=uuid.uuid4(),
            product_reference=self.product_ref,
            quantity=10,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
        )
        
        self.assertTrue(res.is_expired())
        self.assertFalse(res.is_active())
    
    def test_reservation_state_transitions(self):
        """Test state machine transitions."""
        res = StockReservation(
            id=uuid.uuid4(),
            stock_item_id=uuid.uuid4(),
            product_reference=self.product_ref,
            quantity=10,
        )
        
        # Active -> Confirmed
        res.confirm()
        self.assertEqual(res.status, ReservationStatus.CONFIRMED)
        
        # Cannot confirm again
        with self.assertRaises(ValueError):
            res.confirm()


# ===================== Integration Tests =====================

class StockItemModelTests(TestCase):
    """Tests for StockItemModel."""
    
    def test_create_stock_item_model(self):
        """Should create stock item model."""
        item = StockItemModel.objects.create(
            product_id=uuid.uuid4(),
            warehouse_code="MAIN",
            on_hand_quantity=100,
            reserved_quantity=0,
        )
        
        self.assertEqual(item.available_quantity, 100)
        self.assertTrue(item.is_in_stock())
    
    def test_stock_item_unique_constraint(self):
        """Should enforce unique constraint."""
        product_id = uuid.uuid4()
        
        StockItemModel.objects.create(
            product_id=product_id,
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
        
        # Should not be able to create duplicate
        with self.assertRaises(Exception):  # IntegrityError
            StockItemModel.objects.create(
                product_id=product_id,
                warehouse_code="MAIN",
                on_hand_quantity=50,
            )
    
    def test_stock_item_check_constraints(self):
        """Should enforce check constraints."""
        # Cannot create with negative on_hand
        with self.assertRaises(Exception):
            StockItemModel.objects.create(
                product_id=uuid.uuid4(),
                warehouse_code="MAIN",
                on_hand_quantity=-10,
            )


class ReservationModelTests(TestCase):
    """Tests for StockReservationModel."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stock_item = StockItemModel.objects.create(
            product_id=uuid.uuid4(),
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
    
    def test_create_reservation_model(self):
        """Should create reservation model."""
        reservation = StockReservationModel.objects.create(
            reservation_code="RES-TEST-001",
            stock_item=self.stock_item,
            product_id=self.stock_item.product_id,
            quantity=10,
            status=ReservationStatus.ACTIVE.value,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        
        self.assertTrue(reservation.is_active())
        self.assertEqual(reservation.status, ReservationStatus.ACTIVE.value)
    
    def test_reservation_expiry_check(self):
        """Should detect expired reservations."""
        reservation = StockReservationModel.objects.create(
            reservation_code="RES-TEST-002",
            stock_item=self.stock_item,
            product_id=self.stock_item.product_id,
            quantity=10,
            status=ReservationStatus.ACTIVE.value,
            expires_at=timezone.now() - timedelta(hours=1),  # Expired
        )
        
        self.assertTrue(reservation.is_expired())
        self.assertFalse(reservation.is_active())


class MovementModelTests(TestCase):
    """Tests for StockMovementModel."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stock_item = StockItemModel.objects.create(
            product_id=uuid.uuid4(),
            warehouse_code="MAIN",
            on_hand_quantity=100,
        )
    
    def test_create_movement(self):
        """Should create movement record."""
        movement = StockMovementModel.objects.create(
            stock_item=self.stock_item,
            product_id=self.stock_item.product_id,
            movement_type=StockMovementType.STOCK_IN.value,
            quantity=50,
            reference_type="purchase_order",
            reference_id="PO-001",
        )
        
        self.assertEqual(movement.movement_type, StockMovementType.STOCK_IN.value)
        self.assertEqual(movement.quantity, 50)
    
    def test_movements_immutable(self):
        """Movements should not be modifiable."""
        movement = StockMovementModel.objects.create(
            stock_item=self.stock_item,
            product_id=self.stock_item.product_id,
            movement_type=StockMovementType.STOCK_IN.value,
            quantity=50,
        )
        
        # Should not be able to change
        with self.assertRaises(Exception):  # Admin or should be prevented
            StockMovementModel.objects.filter(id=movement.id).delete()
