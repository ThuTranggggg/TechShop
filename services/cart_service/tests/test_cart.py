"""
Comprehensive tests for Cart service.

Tests cover domain logic, models, and integration points.
"""
from decimal import Decimal
from uuid import uuid4, UUID
from django.test import TestCase
from datetime import datetime

from modules.cart.domain.enums import CartStatus, CartItemStatus
from modules.cart.domain.entities import Cart, CartItem
from modules.cart.domain.value_objects import (
    Quantity,
    ProductReference,
    Price,
    ProductSnapshot,
)
from modules.cart.infrastructure.models import CartModel, CartItemModel
from modules.cart.infrastructure.repositories import (
    DjangoCartRepository,
    DjangoCartItemRepository,
)


# ===== Domain Value Object Tests =====

class QuantityValueObjectTests(TestCase):
    """Tests for Quantity value object."""
    
    def test_create_valid_quantity(self):
        """Test creating valid quantity."""
        qty = Quantity(5)
        assert qty.value == 5
    
    def test_quantity_zero_raises_error(self):
        """Test that zero quantity raises error."""
        with self.assertRaises(ValueError):
            Quantity(0)
    
    def test_quantity_negative_raises_error(self):
        """Test that negative quantity raises error."""
        with self.assertRaises(ValueError):
            Quantity(-1)
    
    def test_quantity_increase(self):
        """Test increasing quantity."""
        qty = Quantity(5)
        new_qty = qty.increase(3)
        assert new_qty.value == 8
        # Original unchanged
        assert qty.value == 5
    
    def test_quantity_decrease(self):
        """Test decreasing quantity."""
        qty = Quantity(5)
        new_qty = qty.decrease(2)
        assert new_qty.value == 3
    
    def test_quantity_decrease_below_zero_raises_error(self):
        """Test that decreasing below zero raises error."""
        qty = Quantity(2)
        with self.assertRaises(ValueError):
            qty.decrease(3)
    
    def test_quantity_equality(self):
        """Test quantity equality."""
        qty1 = Quantity(5)
        qty2 = Quantity(5)
        assert qty1 == qty2
    
    def test_quantity_comparison(self):
        """Test quantity comparisons."""
        qty1 = Quantity(5)
        qty2 = Quantity(3)
        assert qty1 > qty2
        assert qty2 < qty1
        assert qty1 >= Quantity(5)


class PriceValueObjectTests(TestCase):
    """Tests for Price value object."""
    
    def test_create_price(self):
        """Test creating price."""
        price = Price(Decimal("99.99"))
        assert price.amount == Decimal("99.99")
        assert price.currency == "USD"
    
    def test_price_from_string(self):
        """Test creating price from string."""
        price = Price("99.99")
        assert price.amount == Decimal("99.99")
    
    def test_price_line_total(self):
        """Test calculating line total."""
        price = Price(Decimal("10.00"))
        qty = Quantity(5)
        total = price.line_total(qty)
        assert total.amount == Decimal("50.00")
    
    def test_negative_price_raises_error(self):
        """Test that negative price raises error."""
        with self.assertRaises(ValueError):
            Price(Decimal("-10.00"))


class ProductSnapshotValueObjectTests(TestCase):
    """Tests for ProductSnapshot value object."""
    
    def test_create_snapshot(self):
        """Test creating product snapshot."""
        snapshot = ProductSnapshot(
            product_id="prod-1",
            name="Samsung Phone",
            slug="samsung-phone",
            brand_name="Samsung",
        )
        assert snapshot.product_id == "prod-1"
        assert snapshot.name == "Samsung Phone"
    
    def test_snapshot_to_dict(self):
        """Test converting snapshot to dict."""
        snapshot = ProductSnapshot(
            product_id="prod-1",
            name="Samsung Phone",
            slug="samsung-phone",
            brand_name="Samsung",
        )
        data = snapshot.to_dict()
        assert data["product_id"] == "prod-1"
        assert data["name"] == "Samsung Phone"


# ===== Domain Entity Tests =====

class CartItemEntityTests(TestCase):
    """Tests for CartItem domain entity."""
    
    def setUp(self):
        """Set up test data."""
        self.cart_id = uuid4()
        self.product_ref = ProductReference("prod-1")
        self.price = Price(Decimal("99.99"))
        self.snapshot = ProductSnapshot(
            product_id="prod-1",
            name="Samsung Phone",
            slug="samsung-phone",
        )
    
    def test_create_cart_item(self):
        """Test creating cart item."""
        item = CartItem(
            id=uuid4(),
            cart_id=self.cart_id,
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        assert item.quantity.value == 2
        assert item.status == CartItemStatus.AVAILABLE
    
    def test_calculate_line_total(self):
        """Test calculating line total."""
        item = CartItem(
            id=uuid4(),
            cart_id=self.cart_id,
            product_reference=self.product_ref,
            quantity=Quantity(3),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        line_total = item.calculate_line_total()
        assert line_total.amount == Decimal("299.97")


class CartAggregateTests(TestCase):
    """Tests for Cart aggregate root."""
    
    def setUp(self):
        """Set up test data."""
        self.user_id = uuid4()
        self.cart = Cart(
            id=uuid4(),
            user_id=self.user_id,
        )
        self.product_ref = ProductReference("prod-1")
        self.price = Price(Decimal("100.00"))
        self.snapshot = ProductSnapshot(
            product_id="prod-1",
            name="Product 1",
            slug="product-1",
        )
    
    def test_create_cart(self):
        """Test creating cart."""
        assert self.cart.user_id == self.user_id
        assert self.cart.status == CartStatus.ACTIVE
        assert self.cart.is_empty()
    
    def test_add_item_to_cart(self):
        """Test adding item to cart."""
        item = self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        assert self.cart.item_count == 1
        assert self.cart.total_quantity == 2
    
    def test_add_same_product_increases_quantity(self):
        """Test adding same product increases quantity instead of creating duplicate."""
        item1 = self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        item2 = self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(3),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        # Should be same item with increased quantity
        assert item1.id == item2.id
        assert self.cart.item_count == 1
        assert self.cart.total_quantity == 5
    
    def test_cart_subtotal(self):
        """Test calculating cart subtotal."""
        self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        assert self.cart.subtotal_amount == 200.00
    
    def test_remove_item(self):
        """Test removing item from cart."""
        item = self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        self.cart.remove_item(item.id)
        assert self.cart.is_empty()
    
    def test_clear_cart(self):
        """Test clearing cart."""
        self.cart.add_item(
            item_id=uuid4(),
            product_reference=self.product_ref,
            quantity=Quantity(2),
            price_snapshot=self.price,
            product_snapshot=self.snapshot,
        )
        self.cart.clear()
        assert self.cart.is_empty()
    
    def test_cannot_modify_checked_out_cart(self):
        """Test that checked out cart cannot be modified."""
        self.cart.mark_checked_out()
        
        with self.assertRaises(RuntimeError):
            self.cart.add_item(
                item_id=uuid4(),
                product_reference=self.product_ref,
                quantity=Quantity(2),
                price_snapshot=self.price,
                product_snapshot=self.snapshot,
            )


# ===== Django Model Tests =====

class CartModelTests(TestCase):
    """Tests for Cart Django ORM model."""
    
    def test_create_cart_model(self):
        """Test creating cart in database."""
        user_id = uuid4()
        cart = CartModel.objects.create(
            id=uuid4(),
            user_id=user_id,
            status=CartStatus.ACTIVE.value,
            currency="USD",
        )
        assert cart.user_id == user_id
        assert cart.status == CartStatus.ACTIVE.value
    
    def test_unique_constraint_one_active_cart_per_user(self):
        """Test unique constraint on active cart per user."""
        user_id = uuid4()
        CartModel.objects.create(
            id=uuid4(),
            user_id=user_id,
            status=CartStatus.ACTIVE.value,
        )
        
        # Trying to create another active cart for same user should fail
        with self.assertRaises(Exception):
            CartModel.objects.create(
                id=uuid4(),
                user_id=user_id,
                status=CartStatus.ACTIVE.value,
            )
    
    def test_can_create_multiple_checked_out_carts(self):
        """Test that multiple checked_out carts can exist per user."""
        user_id = uuid4()
        cart1 = CartModel.objects.create(
            id=uuid4(),
            user_id=user_id,
            status=CartStatus.CHECKED_OUT.value,
        )
        cart2 = CartModel.objects.create(
            id=uuid4(),
            user_id=user_id,
            status=CartStatus.CHECKED_OUT.value,
        )
        assert cart1.id != cart2.id


class CartItemModelTests(TestCase):
    """Tests for CartItem Django ORM model."""
    
    def setUp(self):
        """Set up test data."""
        self.cart = CartModel.objects.create(
            id=uuid4(),
            user_id=uuid4(),
            status=CartStatus.ACTIVE.value,
        )
    
    def test_create_cart_item(self):
        """Test creating cart item."""
        item = CartItemModel.objects.create(
            id=uuid4(),
            cart=self.cart,
            product_id=uuid4(),
            product_name_snapshot="Product Name",
            product_slug_snapshot="product-name",
            quantity=2,
            unit_price_snapshot=Decimal("99.99"),
        )
        assert item.quantity == 2
        assert item.status == CartItemStatus.AVAILABLE.value
    
    def test_unique_product_in_cart_constraint(self):
        """Test unique constraint on product+variant in cart."""
        product_id = uuid4()
        CartItemModel.objects.create(
            id=uuid4(),
            cart=self.cart,
            product_id=product_id,
            product_name_snapshot="Product",
            product_slug_snapshot="product",
            quantity=1,
            unit_price_snapshot=Decimal("99.99"),
        )
        
        # Trying to add same product again should fail
        with self.assertRaises(Exception):
            CartItemModel.objects.create(
                id=uuid4(),
                cart=self.cart,
                product_id=product_id,
                product_name_snapshot="Product",
                product_slug_snapshot="product",
                quantity=1,
                unit_price_snapshot=Decimal("99.99"),
            )


# ===== Repository Tests =====

class DjangoCartRepositoryTests(TestCase):
    """Tests for Django cart repository."""
    
    def setUp(self):
        """Set up test data."""
        self.repo = DjangoCartRepository()
        self.user_id = uuid4()
    
    def test_get_or_create_active_cart(self):
        """Test getting or creating active cart."""
        # Create cart
        cart = Cart(id=uuid4(), user_id=self.user_id)
        saved_cart = self.repo.save(cart)
        assert saved_cart.user_id == self.user_id
        
        # Retrieve same cart
        retrieved = self.repo.get_active_cart_by_user(self.user_id)
        assert retrieved.id == saved_cart.id
    
    def test_only_returns_active_cart(self):
        """Test that only active cart is returned."""
        # Create and checkout a cart
        cart1 = Cart(id=uuid4(), user_id=self.user_id)
        cart1 = self.repo.save(cart1)
        cart1_model = CartModel.objects.get(id=cart1.id)
        cart1_model.status = CartStatus.CHECKED_OUT.value
        cart1_model.save()
        
        # Create another active cart
        cart2 = Cart(id=uuid4(), user_id=self.user_id)
        cart2 = self.repo.save(cart2)
        
        # Should return active cart only
        active = self.repo.get_active_cart_by_user(self.user_id)
        assert active.id == cart2.id


# ===== Integration Tests =====

class CartIntegrationTests(TestCase):
    """Integration tests for cart operations."""
    
    def setUp(self):
        """Set up test data."""
        self.user_id = uuid4()
        self.cart_repo = DjangoCartRepository()
        self.item_repo = DjangoCartItemRepository()
    
    def test_add_item_and_persist(self):
        """Test adding item and persisting to database."""
        # Create cart
        cart = Cart(id=uuid4(), user_id=self.user_id)
        cart = self.cart_repo.save(cart)
        
        # Add item
        product_ref = ProductReference("prod-1")
        item = cart.add_item(
            item_id=uuid4(),
            product_reference=product_ref,
            quantity=Quantity(2),
            price_snapshot=Price(Decimal("99.99")),
            product_snapshot=ProductSnapshot(
                product_id="prod-1",
                name="Product",
                slug="product",
            ),
        )
        self.item_repo.save(item)
        self.cart_repo.save(cart)
        
        # Retrieve and verify
        retrieved_cart = self.cart_repo.get_active_cart_by_user(self.user_id)
        assert retrieved_cart.item_count == 1
        assert retrieved_cart.total_quantity == 2
