# Quick Test Guide - API Contract Fixes

## 🧪 Testing Each Fix

### ISSUE 1: Cart Prices Are Now Numeric

**Quick Test:**
```bash
# 1. Add item to cart
POST http://localhost:8003/api/v1/carts/create/
{
  "field": "value"
}

# 2. Get checkout preview - prices should be NUMBERS, not strings
GET http://localhost:8003/api/v1/checkout-preview/
# Look for: "unit_price": 125.50  (not "125.50")

# 3. Verify in database
psql -h cart_service_db -U cart_service -d cart_service_db
SELECT unit_price_snapshot FROM cart_cartitemmodel;
# Should see: 125.50 (numeric)
```

**Python Test:**
```python
import json
response = requests.get("http://localhost:8003/api/v1/checkout-preview/")
payload = response.json()["data"]["checkout_payload"]
for item in payload["items"]:
    assert isinstance(item["unit_price"], (int, float)), "Price should be numeric!"
    print(f"✅ Price is numeric: {item['unit_price']}")
```

---

### ISSUE 2: Inventory Error Triggers Refund

**Quick Test:**
```bash
# 1. Mock inventory failure by stopping inventory_service
docker-compose stop inventory_service

# 2. Trigger payment callback while inventory is down
POST http://localhost:8001/api/v1/internal/orders/payment-success/
{
  "order_id": "...",
  "payment_id": "..."
}

# Expected response: 
# {
#   "success": false,
#   "message": "Payment succeeded but inventory confirmation failed",
#   "error": "Stock item not found"
# }

# 3. Check order status
GET http://localhost:8001/api/v1/orders/{order_id}/
# Status should be: "payment_failed"

# 4. Check payment service logs for refund
docker-compose logs payment_service
# Should see: "Refund initiated for payment ..."

# 5. Restart inventory
docker-compose start inventory_service
```

**Python Test:**
```python
from unittest.mock import patch

# Test that inventory error triggers refund
with patch("order_service.clients.InventoryServiceClient.confirm_reservations",
           side_effect=ValueError("Not found")):
    with patch("order_service.clients.PaymentServiceClient.refund_payment") as mock_refund:
        try:
            handle_payment_success(order_id, payment_id)
        except ValueError:
            pass
        
        # Assert refund was called
        assert mock_refund.called, "Refund should have been called!"
        print("✅ Refund triggered on inventory error")
```

---

### ISSUE 3: Cannot Cancel During AWAITING_PAYMENT

**Quick Test:**
```bash
# 1. Create order (status becomes AWAITING_PAYMENT)
POST http://localhost:8001/api/v1/orders/from-cart/
{
  "cart_id": "...",
  "shipping_address": {...}
}
# Response: order.status = "awaiting_payment"

# 2. Try to cancel - should FAIL
POST http://localhost:8001/api/v1/orders/{order_id}/cancel/
{
  "reason": "Customer cancelled"
}

# Expected response (400 Bad Request):
# {
#   "success": false,
#   "message": "Cannot cancel order",
#   "errors": {
#     "detail": "Cannot cancel order: payment is being processed..."
#   }
# }

# 3. Try to cancel PENDING order - should SUCCEED
POST http://localhost:8001/api/v1/orders/{pending_order_id}/cancel/
# Response (200 OK): order.status = "cancelled"
```

**Check Order State Machine:**
```python
# Test state transitions
order.status = OrderStatus.PENDING
cancel_service.execute(order_id)  # ✅ Works

order.status = OrderStatus.AWAITING_PAYMENT
try:
    cancel_service.execute(order_id)  # ❌ Should fail
except ValueError as e:
    assert "payment is being processed" in str(e)
    print("✅ Cancel blocked during payment window")
```

---

### ISSUE 4: Reservation Timeout Is 180 Minutes (Configurable)

**Quick Test:**
```bash
# 1. Check config value
python manage.py shell
>>> from django.conf import settings
>>> print(f"Timeout: {settings.STOCK_RESERVATION_TIMEOUT_MINUTES} minutes")
Timeout: 180 minutes

# 2. Override via environment variable
export STOCK_RESERVATION_TIMEOUT_MINUTES=10
python manage.py shell
>>> print(settings.STOCK_RESERVATION_TIMEOUT_MINUTES)
10

# 3. Create reservation and check expiry
POST /api/v1/internal/inventory/reserve/
# Check database:
SELECT expires_at, NOW() FROM stock_reservations 
WHERE id = 'reservation_id';
# expires_at should be ~180 minutes (or 10 minutes if overridden) from NOW()

# 4. Wait for Celery task to run (every hour) and check logs
docker-compose logs inventory_service | grep "Expired reservation cleanup"
# Should see: "Expired reservation cleanup: released=N, errors=0"
```

**Force Test Cleanup Task:**
```bash
# Run cleanup task manually
python manage.py shell
>>> from modules.inventory.tasks import release_expired_reservations
>>> result = release_expired_reservations()
>>> print(result)
{'status': 'success', 'released_count': 123, 'error_count': 0, 'total_expired': 123}
```

**Python Test:**
```python
from modules.inventory.models import StockReservationModel
from modules.inventory.tasks import release_expired_reservations
from datetime import datetime, timedelta
from django.utils import timezone

# Create expired reservation (100 minutes old, 180 min timeout)
reservation = StockReservationModel.objects.create(
    product_id="prod-1",
    quantity=5,
    status="active",
    expires_at=timezone.now() - timedelta(minutes=100),
)

stock_before = reservation.stock_item.on_hand_quantity

# Run cleanup
release_expired_reservations()

# Check: stock was released
stock_after = reservation.stock_item.on_hand_quantity
assert stock_after == stock_before + 5, "Stock should be released!"
print("✅ Expired reservation auto-released")
```

---

## 🔍 Integration Test - Complete Flow

```python
def test_complete_checkout_to_delivery():
    """End-to-end test of all 4 fixes working together."""
    
    # SETUP
    user_id = create_user()
    product_id = create_product(price=Decimal("100.00"))
    
    # FIX 1: Add to cart with numeric prices
    cart = add_to_cart(user_id, product_id, qty=2)
    preview = get_checkout_preview(cart.id)
    assert isinstance(preview["checkout_payload"]["unit_price"], float)
    print("✅ FIX 1: Prices are numeric")
    
    # FIX 3: Try to cancel PENDING order (before payment)
    order = create_order_from_cart(user_id, cart.id)
    cancel_order(order.id)  # Should work
    assert order.status == OrderStatus.CANCELLED
    print("✅ FIX 3: Can cancel PENDING orders")
    
    # Create new order for payment flow
    order = create_order_from_cart(user_id, new_cart.id)
    assert order.status == OrderStatus.AWAITING_PAYMENT
    
    # FIX 3: Try to cancel during AWAITING_PAYMENT (should FAIL)
    try:
        cancel_order(order.id)
        assert False, "Should not reach here!"
    except ValueError as e:
        assert "payment is being processed" in str(e)
    print("✅ FIX 3: Cannot cancel AWAITING_PAYMENT")
    
    # FIX 2: Test payment success with inventory error
    with patch.object(inventory_client, 'confirm_reservations',
                      side_effect=ValueError("Not found")):
        with patch.object(payment_client, 'refund_payment') as mock_refund:
            try:
                handle_payment_success(order.id, "payment-123")
                assert False, "Should have raised error!"
            except ValueError:
                pass
            
            # Assert refund was triggered
            assert mock_refund.called
    
    order.refresh_from_db()
    assert order.status == OrderStatus.PAYMENT_FAILED
    print("✅ FIX 2: Inventory error triggers refund")
    
    # FIX 4: Check reservation timeout is 180 minutes
    from django.conf import settings
    assert settings.STOCK_RESERVATION_TIMEOUT_MINUTES == 180
    print("✅ FIX 4: Timeout is 180 minutes")
    
    print("\n🎉 All 4 fixes verified!")
```

---

## 📊 Monitoring Checks

### Health Checks
```bash
# Cart Service - Prices are numeric
curl http://localhost:8003/health
# Response should have: "status": "ok"

# Order Service - Payment error handling works
curl http://localhost:8001/health

# Inventory Service - Timeout config loaded
curl http://localhost:8007/health
# Should include: STOCK_RESERVATION_TIMEOUT_MINUTES: 180
```

### Log Tailing
```bash
# Monitor ISSUE 2: Inventory confirmation errors
docker-compose logs -f order_service | grep INVENTORY_CONFIRMATION_ERROR

# Monitor ISSUE 4: Expired reservation cleanup
docker-compose logs -f inventory_service | grep "Expired reservation cleanup"

# Monitor ISSUE 3: Cancel attempts during AWAITING_PAYMENT
docker-compose logs -f order_service | grep "payment is being processed"
```

### Database Checks
```sql
-- Check ISSUE 1: Prices are Decimal in DB
SELECT unit_price_snapshot, typeof(unit_price_snapshot) FROM cart_cartitemmodel LIMIT 5;

-- Check ISSUE 4: Reservations have correct expiry
SELECT id, quantity, expires_at, (expires_at - NOW()) as time_remaining 
FROM stock_reservations 
WHERE status = 'active' 
LIMIT 5;

-- Check ISSUE 2 & 3: Order statuses
SELECT id, status, payment_status, created_at 
FROM order_ordermodel 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## ✅ Success Criteria

| Issue | Success Criteria | How to Verify |
|-------|------------------|---------------|
| 1 | Prices are JSON numbers | `typeof(unit_price) !== "string"` |
| 2 | Refund on inventory error | Refund called when confirm fails |
| 3 | Cancel blocked mid-payment | 400 error when status=AWAITING_PAYMENT |
| 4 | Timeout is 180 minutes | Check settings + check DB expires_at |

All criteria must be green ✅ before production deployment!
