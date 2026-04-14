# Cart Service - Verification Checklist

Use this checklist to verify that cart_service is correctly set up and all components are working.

## Pre-Setup (Dependencies)

- [ ] **Step 1:** Product Service is running or accessible via HTTP
- [ ] **Step 2:** Inventory Service is running or accessible via HTTP
- [ ] **Step 3:** PostgreSQL is running (for cart_service_db)
- [ ] **Step 4:** Verify Python 3.9+ installed: `python --version`
- [ ] **Step 5:** Verify pip installed: `pip --version`

## Setup Phase

- [ ] **Step 6:** Copy .env.example to .env: `cp .env.example .env`
- [ ] **Step 7:** Update .env with correct service URLs:
  ```
  PRODUCT_SERVICE_URL=http://product_service:8006
  INVENTORY_SERVICE_URL=http://inventory_service:8007
  ```
- [ ] **Step 8:** Install dependencies: `pip install -r requirements.txt`
- [ ] **Step 9:** Verify Django: `python manage.py --version`
- [ ] **Step 10:** Create database tables: `python manage.py migrate`

## Initial Data (Optional)

- [ ] **Step 11:** Seed demo carts: `python manage.py seed_carts`
- [ ] **Step 12:** Verify seed created records:
  ```bash
  python manage.py dbshell
  SELECT COUNT(*) FROM cart_cartmodel;
  SELECT COUNT(*) FROM cart_cartitemmodel;
  \q
  ```
- [ ] **Step 13:** Create admin user (optional): `python manage.py createsuperuser`

## Server Startup

- [ ] **Step 14:** Start development server: `python manage.py runserver 0.0.0.0:8003`
- [ ] **Step 15:** Verify server started:
  ```bash
  curl http://localhost:8003/health/
  # Should return: {"success": true}
  ```
- [ ] **Step 16:** Check health via API: 
  ```bash
  curl http://localhost:8003/api/v1/health/
  ```

## API Documentation

- [ ] **Step 17:** Open Swagger UI: http://localhost:8003/api/docs/
- [ ] **Step 18:** Verify schema loads: http://localhost:8003/api/schema/
- [ ] **Step 19:** All cart endpoints listed in docs

## Test Execution

- [ ] **Step 20:** Run all tests: `python manage.py test tests/`
- [ ] **Step 21:** Verify all tests pass (should see "OK")
- [ ] **Step 22:** Run specific test class: `python manage.py test tests.test_cart.CartAggregateTests`

## Admin Interface

- [ ] **Step 23:** Access admin: http://localhost:8003/admin/
- [ ] **Step 24:** Login with created superuser credentials
- [ ] **Step 25:** Verify Cart model visible in admin
- [ ] **Step 26:** Verify CartItem model visible in admin
- [ ] **Step 27:** View created carts in admin
- [ ] **Step 28:** View cart items in admin

## Manual API Testing (Curl)

### Setup User ID
```bash
export USER_ID="550e8400-e29b-41d4-a716-446655440000"
export PRODUCT_ID="f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

### Get Cart
- [ ] **Step 29:** Get current cart:
```bash
curl -X GET http://localhost:8003/api/v1/cart/current/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with empty or seeded cart

### Add Item
- [ ] **Step 30:** Add item to cart:
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/ \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "'$PRODUCT_ID'",
    "quantity": 2
  }'
```
Expected: 201 Created with item added to cart

- [ ] **Step 31:** Verify item count increased (get cart again)

### Update Quantity
- [ ] **Step 32:** Get item ID from cart, then update:
```bash
ITEM_ID="<id from previous response>"
curl -X PATCH http://localhost:8003/api/v1/cart/items/$ITEM_ID/quantity/ \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"new_quantity": 5}'
```
Expected: 200 OK with updated quantity

### Increase/Decrease
- [ ] **Step 33:** Increase quantity:
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/$ITEM_ID/increase/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with quantity +1

- [ ] **Step 34:** Decrease quantity:
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/$ITEM_ID/decrease/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with quantity -1

### Cart Summary
- [ ] **Step 35:** Get cart summary:
```bash
curl -X GET http://localhost:8003/api/v1/cart/summary/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with {item_count, total_quantity, subtotal_amount, currency}

### Cart Refresh
- [ ] **Step 36:** Refresh cart snapshots:
```bash
curl -X POST http://localhost:8003/api/v1/cart/refresh/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with refreshed items

### Cart Validation
- [ ] **Step 37:** Validate cart:
```bash
curl -X POST http://localhost:8003/api/v1/cart/validate/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with {is_valid: true, issues: []}

### Checkout Preview
- [ ] **Step 38:** Get checkout preview:
```bash
curl -X POST http://localhost:8003/api/v1/cart/checkout-preview/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with {is_valid, cart, issues, checkout_payload}

### Clear Cart
- [ ] **Step 39:** Clear cart:
```bash
curl -X POST http://localhost:8003/api/v1/cart/clear/ \
  -H "X-User-ID: $USER_ID"
```
Expected: 200 OK with empty cart

- [ ] **Step 40:** Verify cart empty: get cart again should show item_count: 0

## Internal (Service-to-Service) API Testing

### Setup Key
```bash
export INTERNAL_KEY="your-internal-service-key-here"
export CART_ID="<cart id from earlier>"
```

### Get Active Cart (Internal)
- [ ] **Step 41:** Internal get active cart:
```bash
curl -X GET http://localhost:8003/api/v1/internal/carts/users/$USER_ID/active/ \
  -H "X-Internal-Service-Key: $INTERNAL_KEY"
```
Expected: 200 OK with active cart

### Get Cart by ID (Internal)
- [ ] **Step 42:** Internal get cart by ID:
```bash
curl -X GET http://localhost:8003/api/v1/internal/carts/$CART_ID/ \
  -H "X-Internal-Service-Key: $INTERNAL_KEY"
```
Expected: 200 OK with cart details

### Mark Checked Out (Internal)
- [ ] **Step 43:** Mark cart checked out:
```bash
curl -X POST http://localhost:8003/api/v1/internal/carts/$CART_ID/mark-checked-out/ \
  -H "X-Internal-Service-Key: $INTERNAL_KEY"
```
Expected: 200 OK with status changed to "checked_out"

- [ ] **Step 44:** Verify cart is now checked out: status should be "checked_out"

### Get Checkout Payload (Internal)
- [ ] **Step 45:** Get checkout payload:
```bash
# First create new cart and add item
curl -X POST http://localhost:8003/api/v1/cart/items/ \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "'$PRODUCT_ID'", "quantity": 1}'

# Get new cart ID, then get payload
curl -X POST http://localhost:8003/api/v1/internal/carts/$NEW_CART_ID/checkout-payload/ \
  -H "X-Internal-Service-Key: $INTERNAL_KEY"
```
Expected: 200 OK with checkout payload including cart, items, totals

## Permission Testing

### Missing User ID
- [ ] **Step 46:** API call without X-User-ID should fail:
```bash
curl -X GET http://localhost:8003/api/v1/cart/current/
```
Expected: 401 Unauthorized

### Invalid Internal Key
- [ ] **Step 47:** Internal API without key should fail (if key required):
```bash
curl -X GET http://localhost:8003/api/v1/internal/carts/users/$USER_ID/active/
```
Expected: 401 Unauthorized (may vary based on dev mode)

## Error Handling

### Invalid Product ID
- [ ] **Step 48:** Try adding non-existent product:
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/ \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}'
```
Expected: 400 Bad Request with error message

### Invalid Quantity
- [ ] **Step 49:** Try adding with quantity 0:
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/ \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "'$PRODUCT_ID'", "quantity": 0}'
```
Expected: 400 Bad Request

### Insufficient Inventory (if applicable)
- [ ] **Step 50:** Try adding quantity exceeding available inventory (requires inventory_service)
Expected: 400 Bad Request

## Final Verification

- [ ] **Step 51:** All tests pass: `python manage.py test tests/ --verbosity=2`
- [ ] **Step 52:** No migration issues: `python manage.py showmigrations modules.cart`
- [ ] **Step 53:** Admin interface working: http://localhost:8003/admin/
- [ ] **Step 54:** API docs complete: http://localhost:8003/api/docs/
- [ ] **Step 55:** Database clean:
  ```bash
  python manage.py dbshell
  SELECT table_name FROM information_schema.tables WHERE table_schema='public';
  \q
  ```
  Should see: cart_cartmodel and cart_cartitemmodel

## Status Summary

**Core Functionality:**
- [ ] Product validation (via product_service)
- [ ] Inventory checking (via inventory_service)
- [ ] Cart CRUD operations
- [x] Snapshot storage
- [ ] Price tracking
- [ ] Checkout preview

**Admin & Docs:**
- [ ] Admin interface
- [ ] API documentation
- [ ] Schema file

**Testing:**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Permission tests pass
- [ ] Error handling works

**Deployment:**
- [ ] Migrations runnable
- [ ] Seed data works
- [ ] Server starts cleanly
- [ ] Logs appropriate

## Sign-Off

Once all steps are complete:

```
Verification Date: _______________
Verified By: _______________________
Environment: Production / Staging / Local
Last Test Run: _______________________
Issues Found: None / See attached notes
Ready for: Integration / Deployment
```

## Troubleshooting

If any verification step fails, refer to [README.md](README.md) or [CART_SERVICE.md](CART_SERVICE.md).

Common issues:
1. **Product/Inventory service unavailable** → Check PRODUCT_SERVICE_URL and INVENTORY_SERVICE_URL in .env
2. **Database connection failed** → Verify DB_HOST, DB_PORT, DB_NAME, DB_USER in .env
3. **Migration errors** → Ensure Django migration files valid with `python manage.py makemigrations --dry-run`
4. **Port 8003 already in use** → Change SERVICE_PORT in .env or kill process using port
5. **Internal key auth failing** → Ensure INTERNAL_SERVICE_KEY matches in .env
