# Shipping Service - Installation & Verification Checklist

## Pre-Installation

- [ ] PostgreSQL is running
- [ ] Python 3.11+ is available
- [ ] Virtual environment is activated
- [ ] Django project structure is intact

## Installation Steps

### 1. Database Setup
```bash
# From shipping_service root directory
python manage.py makemigrations modules.shipping
python manage.py migrate modules.shipping
```

- [ ] Migrations created successfully
- [ ] No migration conflicts
- [ ] Database tables created (verify with admin or psql)

### 2. Django Configuration
```bash
# Verify settings.py
grep "modules.shipping" config/settings.py
```

- [ ] `modules.shipping` is in INSTALLED_APPS
- [ ] `INTERNAL_SERVICE_KEY` is configured
- [ ] PostgreSQL database connection is correct

### 3. URL Configuration
```bash
# Verify urls.py
grep "shipping.urls" config/urls.py
```

- [ ] Shipping URLs are included in config/urls.py
- [ ] URL pattern uses correct path prefix `/api/v1/`

## Verification Checklist

### A. Service Health

```bash
# Check service is running
curl http://localhost:8006/health/ -i
```

- [ ] HTTP 200 response
- [ ] "status": "healthy" in response

### B. Database Connection

```bash
# Check database health endpoint
curl http://localhost:8006/api/v1/health/ -i
```

- [ ] HTTP 200 response
- [ ] No database connection errors in logs

### C. Models & Migrations

```bash
# List all shipping models
python manage.py sqlmigrations modules.shipping
```

- [ ] 3 models present:
  - [ ] ShipmentModel
  - [ ] ShipmentItemModel
  - [ ] ShipmentTrackingEventModel
- [ ] All indexes created
- [ ] No pending migrations

### D. Admin Interface

```bash
# Check admin is accessible
open http://localhost:8006/admin/
```

- [ ] Admin login page loads
- [ ] Shipping models visible:
  - [ ] Shipments
  - [ ] Shipment Items
  - [ ] Shipment Tracking Events
- [ ] Color-coded status display visible

### E. API Schema & Documentation

```bash
# Check Swagger documentation
open http://localhost:8006/api/docs/
```

- [ ] Swagger UI loads
- [ ] All shipping endpoints listed:
  - [ ] /api/v1/internal/shipments/ (POST)
  - [ ] /api/v1/internal/shipments/ (GET)
  - [ ] /api/v1/shipments/ endpoints
  - [ ] /api/v1/mock-shipments/ endpoints
- [ ] Endpoints are properly documented
- [ ] Request/response schemas visible

### F. Internal API (Protected)

```bash
# Test creating shipment
curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: dev-key-change-in-production" \
  -d '{
    "order_id": "test-order-001",
    "order_number": "ORD-TEST-001",
    "user_id": "test-user-001",
    "receiver_name": "Test Customer",
    "receiver_phone": "0912345678",
    "address_line1": "123 Main St",
    "ward": "Ward 1",
    "district": "District 1",
    "city": "Ho Chi Minh",
    "country": "VN",
    "postal_code": "70000",
    "items": [{
      "product_id": "test-prod-001",
      "product_name": "Test Product",
      "sku": "TEST-001",
      "quantity": 1,
      "unit_price": 100000,
      "total_price": 100000
    }],
    "service_level": "standard",
    "provider": "mock",
    "shipping_fee_amount": 50000,
    "currency": "VND"
  }' -i
```

- [ ] HTTP 201 Created response
- [ ] Response contains `shipment_reference` (e.g., SHIP-xxxxx)
- [ ] Response contains `tracking_number`
- [ ] Response contains `status: "CREATED"`

### G. Public API (No Auth)

```bash
# Extract shipment_reference from test above, then:
curl http://localhost:8006/api/v1/shipments/SHIP-xxxxx/tracking/ -i
```

- [ ] HTTP 200 OK response
- [ ] Response contains events array
- [ ] Response contains current_status
- [ ] Response accessible without authentication

### H. Mock API (Development)

```bash
# Test mock advancement
curl -X POST http://localhost:8006/api/v1/mock-shipments/SHIP-xxxxx/advance/ \
  -H "Content-Type: application/json" \
  -H "X-Mock-Enabled: true" \
  -d '{"target_status": "DELIVERED"}' -i
```

- [ ] HTTP 200 OK response
- [ ] Response indicates shipment advanced to target status
- [ ] Response shows transition path used

### I. State Transitions

```bash
# Test marking shipment as picked up
curl -X POST http://localhost:8006/api/v1/internal/shipments/SHIP-xxxxx/mark-picked-up/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production" -i
```

- [ ] HTTP 200 OK response
- [ ] Status changed to "PICKED_UP"
- [ ] Timestamp updated

```bash
# Continue transitions
curl -X POST http://localhost:8006/api/v1/internal/shipments/SHIP-xxxxx/mark-in-transit/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production" -i
```

- [ ] HTTP 200 OK response
- [ ] Status changed to "IN_TRANSIT"

### J. Tracking Timeline

```bash
# Verify tracking events accumulate
curl http://localhost:8006/api/v1/shipments/SHIP-xxxxx/tracking/ -i
```

- [ ] Events array contains multiple entries:
  - [ ] CREATED event
  - [ ] PICKED_UP event
  - [ ] DISPATCHED event
  - [ ] IN_HUB event (if applicable)
- [ ] Events are ordered chronologically
- [ ] Each event has timestamp, location, notes

### K. Admin Interface Data

```bash
# Verify admin shows data
open http://localhost:8006/admin/shipping/shipmentmodel/
```

- [ ] Shipments appear in list
- [ ] Shipment reference visible
- [ ] Status color-coded:
  - [ ] CREATED (gray)
  - [ ] PENDING_PICKUP (orange)
  - [ ] PICKED_UP (sky blue)
  - [ ] IN_TRANSIT (royal blue)
  - [ ] DELIVERED (green)
- [ ] Can click to view full details

### L. Inline Relations in Admin

- [ ] Click on shipment detail
- [ ] ShipmentItems inline visible (if created)
- [ ] ShipmentTrackingEvents inline visible with timeline
- [ ] Timeline is read-only (cannot edit events)

### M. Test Suite

```bash
# Run all shipping tests
python manage.py test modules.shipping.tests -v 2
```

- [ ] All tests pass
- [ ] No migration errors
- [ ] Test output shows:
  - [ ] test_services.py tests passing
  - [ ] test_models.py tests passing
  - [ ] Minimum 13+ service tests
  - [ ] Minimum 20+ model tests

### N. Permission Guards

```bash
# Test missing internal service key
curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -d '{}' -i
```

- [ ] HTTP 403 Forbidden response
- [ ] "Permission denied" or similar message

### O. Error Handling

```bash
# Test validation errors
curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: dev-key-change-in-production" \
  -d '{"order_id": ""}' -i
```

- [ ] HTTP 400 Bad Request response
- [ ] Error message indicates validation failure
- [ ] Error details list specific field problems

### P. Database Constraints

```bash
# Try creating duplicate shipment reference (in Django shell)
python manage.py shell
```

```python
from modules.shipping.infrastructure.models import ShipmentModel
from modules.shipping.domain.entities import ShipmentStatus

# Try duplicate reference
try:
    ShipmentModel.objects.create(
        shipment_reference="DUPLICATE",
        order_id="order-1",
        user_id="user-1",
        tracking_number="TRACK-1",
        status=ShipmentStatus.CREATED.value,
        receiver_address={"name": "Test"},
        total_items=1,
        total_weight=1.0,
        total_price=100000,
        service_level="standard",
        provider="mock",
        shipping_fee_amount=25000,
        currency="VND",
    )
    ShipmentModel.objects.create(
        shipment_reference="DUPLICATE",  # Should fail
        order_id="order-2",
        user_id="user-2",
        tracking_number="TRACK-2",
        status=ShipmentStatus.CREATED.value,
        receiver_address={"name": "Test"},
        total_items=1,
        total_weight=1.0,
        total_price=100000,
        service_level="standard",
        provider="mock",
        shipping_fee_amount=25000,
        currency="VND",
    )
except Exception as e:
    print(f"✓ Constraint enforced: {e}")
```

- [ ] IntegrityError raised for duplicate reference
- [ ] Database constraint working correctly

### Q. Idempotency

```bash
# Mark as delivered twice
curl -X POST http://localhost:8006/api/v1/internal/shipments/SHIP-xxxxx/mark-delivered/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production"

# Second call
curl -X POST http://localhost:8006/api/v1/internal/shipments/SHIP-xxxxx/mark-delivered/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production"
```

- [ ] Both calls return HTTP 200 OK
- [ ] Same delivery date returned both times
- [ ] No duplicate events created
- [ ] Status remains DELIVERED

## Optional: Order Service Integration

If order_service is running:

```bash
# Configure ORDER_SERVICE_URL in settings.py
# Then create a shipment
curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: dev-key-change-in-production" \
  -d '{ ... }'
```

- [ ] Shipment created successfully
- [ ] Check order_service logs for notification:
  - [ ] shipment_created event received
  - [ ] order status updated
- [ ] Mark delivered
  - [ ] shipment_delivered notification sent
  - [ ] order_status reflects delivery

## Post-Verification

### Things to Test Manually

- [ ] Complete end-to-end workflow (create → deliver)
- [ ] Retrieve shipment by reference through public API
- [ ] Check tracking page shows all events
- [ ] Verify admin color-coded display
- [ ] Test cancellation (from CREATED state only)
- [ ] Test invalid state transition (try to go backward)
- [ ] Try accessing mock endpoints with DEBUG=False and no header (should fail)

### Documentation Review

- [ ] README_SHIPPING.md looks complete
- [ ] SHIPPING_SERVICE_QUICK_REFERENCE.md has all examples
- [ ] SHIPPING_SERVICE_IMPLEMENTATION_SUMMARY.md is accurate
- [ ] Code comments are present on key methods
- [ ] Test files have docstrings explaining test purpose

### Logs & Monitoring

```bash
# Check logs for errors
tail -f logs/shipping_service.log  # If configured

# Or from Django management:
python manage.py runserver 0.0.0.0:8006 2>&1 | grep -i error
```

- [ ] No ERROR level logs for normal operations
- [ ] INFO level logs for create/deliver operations
- [ ] DEBUG logs show query details (in DEBUG mode)
- [ ] No unhandled exceptions

### Performance Check

```bash
# Testing with multiple shipments
for i in {1..5}; do
  curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
    -H "Content-Type: application/json" \
    -H "X-Internal-Service-Key: dev-key-change-in-production" \
    -d '{ ... }'
done

# Time a query
time curl http://localhost:8006/api/v1/shipments/SHIP-xxxxx/tracking/
```

- [ ] Create shipment takes < 500ms
- [ ] Get tracking takes < 100ms
- [ ] Database queries use indexes (check EXPLAIN in logs)
- [ ] No N+1 query problems

## Troubleshooting

If any checklist item fails:

### Issue: "Module not found"
- [ ] Verify `modules.shipping.*` in config/settings.py INSTALLED_APPS
- [ ] Check `modules/shipping/` directory exists
- [ ] Verify `modules/shipping/__init__.py` exists

### Issue: "Table does not exist"
- [ ] Run: `python manage.py migrate modules.shipping`
- [ ] Check PostgreSQL is running
- [ ] Verify database name and credentials

### Issue: "Permission denied" on internal API
- [ ] Verify `X-Internal-Service-Key: dev-key-change-in-production` header
- [ ] Check INTERNAL_SERVICE_KEY in settings.py
- [ ] If DEBUG=True, localhost access might be allowed

### Issue: Tests fail
- [ ] Ensure migrations ran: `python manage.py migrate`
- [ ] Check database is accessible
- [ ] Review test output for specific errors
- [ ] Verify test database settings in tests

### Issue: Admin models not showing
- [ ] Verify `modules.shipping` is in INSTALLED_APPS
- [ ] Restart Django server
- [ ] Clear browser cache
- [ ] Check modules/shipping/presentation/admin.py registers models

### Issue: Order service notifications failing
- [ ] Verify order_service is running
- [ ] Check ORDER_SERVICE_URL configuration
- [ ] Check network connectivity
- [ ] Review shipping service logs for HTTP errors

## Sign-Off

Once all items are checked:

```
✅ Shipping Service Fully Operational

Date Verified: ___________
Verified By: ___________
Environment: [ ] Local [ ] Staging [ ] Production
Notes: _________________________________
```

---

**Next Steps**:
1. Report successful verification
2. Deploy to staging environment
3. Integration testing with other services
4. Load testing (if needed)
5. Production deployment

**Support**: See README_SHIPPING.md for detailed documentation or SHIPPING_SERVICE_QUICK_REFERENCE.md for API examples.
