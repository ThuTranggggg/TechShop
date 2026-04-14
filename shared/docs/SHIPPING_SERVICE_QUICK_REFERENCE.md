# Shipping Service - Quick API Reference

## Quick Start

### Health Check
```bash
curl http://localhost:8006/health/
```

### API Schema
```bash
# JSON schema
curl http://localhost:8006/api/schema/

# Swagger UI
open http://localhost:8006/api/docs/
```

### Admin Interface
```
http://localhost:8006/admin/
Username: (your superuser)
Password: (your superuser)
```

---

## Internal API (For order_service)

**Auth Header**: `X-Internal-Service-Key: dev-key-change-in-production`

### Create Shipment
```bash
POST /api/v1/internal/shipments/
Content-Type: application/json

{
  "order_id": "order-456",
  "order_number": "ORD-001",
  "user_id": "user-789",
  "receiver_name": "John Doe",
  "receiver_phone": "0912345678",
  "address_line1": "123 Main St",
  "address_line2": "Apt 4B",
  "ward": "Ward 1",
  "district": "District 1",
  "city": "Ho Chi Minh City",
  "country": "VN",
  "postal_code": "70000",
  "items": [
    {
      "product_id": "prod-001",
      "product_name": "Product A",
      "sku": "SKU-001",
      "quantity": 2,
      "unit_price": 100000,
      "total_price": 200000
    }
  ],
  "service_level": "standard",
  "provider": "mock",
  "shipping_fee_amount": 50000,
  "currency": "VND"
}

# Response (201 Created)
{
  "success": true,
  "data": {
    "id": "12345678-1234-1234-1234-123456789012",
    "shipment_reference": "SHIP-ABC123",
    "tracking_number": "VNP-XYZ789",
    "order_id": "order-456",
    "status": "CREATED",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Shipment by ID
```bash
GET /api/v1/internal/shipments/{id}/
Content-Type: application/json

# or specific shipment
GET /api/v1/internal/shipments/reference/SHIP-ABC123/
GET /api/v1/internal/shipments/order/order-456/
```

### Mark Shipment Picked Up
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/mark-picked-up/
Content-Type: application/json

# Response (200 OK)
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "status": "PICKED_UP",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### Mark Shipment In Transit
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/mark-in-transit/
Content-Type: application/json

{
  "location": "Distribution Hub A"
}
```

### Mark Out For Delivery
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/mark-out-for-delivery/
Content-Type: application/json

{
  "location": "Local Delivery Hub"
}
```

### Mark Delivered
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/mark-delivered/
Content-Type: application/json

{
  "location": "Customer Address"
}

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "status": "DELIVERED",
    "actual_delivery_date": "2024-01-15T14:30:00Z"
  }
}
```

### Mark Failed Delivery
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/mark-failed-delivery/
Content-Type: application/json

{
  "failure_reason": "Customer not home"
}
```

### Cancel Shipment
```bash
POST /api/v1/internal/shipments/SHIP-ABC123/cancel/
Content-Type: application/json

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "status": "CANCELLED"
  }
}
```

---

## Public API (For Customers)

**No Authentication Required**

### Get Shipment Detail
```bash
GET /api/v1/shipments/SHIP-ABC123/

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "tracking_number": "VNP-XYZ789",
    "status": "IN_TRANSIT",
    "provider": "mock",
    "receiver_address": {
      "name": "John Doe",
      "phone": "0912345678",
      "city": "Ho Chi Minh"
    },
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Shipment Status
```bash
GET /api/v1/shipments/SHIP-ABC123/status/

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "status": "IN_TRANSIT",
    "expected_delivery_date": "2024-01-17",
    "last_update": "2024-01-15T14:30:00Z"
  }
}
```

### Get Tracking Timeline
```bash
GET /api/v1/shipments/SHIP-ABC123/tracking/

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "tracking_number": "VNP-XYZ789",
    "current_status": "IN_TRANSIT",
    "events": [
      {
        "event_type": "CREATED",
        "status": "CREATED",
        "location": "Warehouse",
        "timestamp": "2024-01-15T10:30:00Z",
        "notes": "Shipment created"
      },
      {
        "event_type": "PICKED_UP",
        "status": "PICKED_UP",
        "location": "Warehouse",
        "timestamp": "2024-01-15T12:00:00Z",
        "notes": null
      },
      {
        "event_type": "DISPATCHED",
        "status": "IN_TRANSIT",
        "location": "Distribution Hub A",
        "timestamp": "2024-01-15T14:30:00Z",
        "notes": "In transit"
      }
    ]
  }
}
```

---

## Mock API (For Development/Testing)

**Auth Header**: `X-Mock-Enabled: true` (or DEBUG=True)

### Auto-Advance Shipment Status
```bash
POST /api/v1/mock-shipments/SHIP-ABC123/advance/
Content-Type: application/json

{
  "target_status": "DELIVERED"
}

# Response
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-ABC123",
    "status": "DELIVERED",
    "message": "Shipment advanced from CREATED to DELIVERED"
  }
}
```

### Valid Target Statuses
- PENDING_PICKUP
- PICKED_UP
- IN_TRANSIT
- OUT_FOR_DELIVERY
- DELIVERED
- FAILED_DELIVERY
- CANCELLED

**Example**: Service will auto-transition through CREATED → PENDING_PICKUP → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED

---

## Common cURL Examples

### Create Shipment
```bash
curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: dev-key-change-in-production" \
  -d '{
    "order_id": "order-456",
    "order_number": "ORD-001",
    "user_id": "user-789",
    "receiver_name": "John Doe",
    "receiver_phone": "0912345678",
    "address_line1": "123 Main St",
    "ward": "Ward 1",
    "district": "District 1",
    "city": "Ho Chi Minh City",
    "country": "VN",
    "postal_code": "70000",
    "items": [{
      "product_id": "prod-001",
      "product_name": "Product A",
      "sku": "SKU-001",
      "quantity": 2,
      "unit_price": 100000,
      "total_price": 200000
    }],
    "service_level": "standard",
    "provider": "mock",
    "shipping_fee_amount": 50000,
    "currency": "VND"
  }'
```

### Get Public Tracking
```bash
curl http://localhost:8006/api/v1/shipments/SHIP-ABC123/tracking/
```

### Mark Delivered (Internal)
```bash
curl -X POST http://localhost:8006/api/v1/internal/shipments/SHIP-ABC123/mark-delivered/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production"
```

### Auto-Advance in Mock
```bash
curl -X POST http://localhost:8006/api/v1/mock-shipments/SHIP-ABC123/advance/ \
  -H "Content-Type: application/json" \
  -H "X-Mock-Enabled: true" \
  -d '{"target_status": "DELIVERED"}'
```

---

## State Machine Reference

```
CREATED (Initial state)
  ├─ To: PENDING_PICKUP (normal flow)
  ├─ To: CANCELLED (before pickup)
  └─ Terminal: NO

PENDING_PICKUP (Awaiting pickup)
  ├─ To: PICKED_UP (normal flow)
  ├─ To: CANCELLED (before picked up)
  └─ Terminal: NO

PICKED_UP (Picked from sender)
  ├─ To: IN_TRANSIT (normal flow)
  └─ Terminal: NO

IN_TRANSIT (In carrier network)
  ├─ To: OUT_FOR_DELIVERY (normal flow)
  └─ Terminal: NO

OUT_FOR_DELIVERY (On delivery vehicle)
  ├─ To: DELIVERED (success)
  ├─ To: FAILED_DELIVERY (failed attempt)
  └─ Terminal: NO

DELIVERED ✓ (Successfully delivered)
  ├─ Terminal: YES (no further transitions)
  └─ Idempotent: OK to call mark-delivered again

FAILED_DELIVERY (Delivery failed)
  ├─ To: OUT_FOR_DELIVERY (retry)
  └─ Terminal: NO

RETURNED (Returned to sender)
  ├─ Terminal: YES
  └─ Notes: Treated as terminal for MVP

CANCELLED ✗ (Cancelled)
  ├─ Terminal: YES
  └─ Notes: Only from CREATED or PENDING_PICKUP
```

---

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    "shipment_reference": "...",
    ...
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message here",
  "errors": {
    "field_name": ["error detail"]
  }
}
```

### Common HTTP Status Codes
- `200 OK` - Success (GET, successful state transition)
- `201 Created` - Resource created (POST create shipment)
- `400 Bad Request` - Validation error (invalid data)
- `404 Not Found` - Shipment not found
- `500 Internal Server Error` - Server error (check logs)

---

## Troubleshooting

### "Shipment not found"
- Check shipment reference format (SHIP-xxxxx)
- Verify shipment exists in database
- Use admin interface to verify

### "Permission denied"
- Check X-Internal-Service-Key header (should be `dev-key-change-in-production`)
- Verify service calling has correct key configured
- For mock APIs, add `X-Mock-Enabled: true` header or ensure DEBUG=True

### "Invalid state transition"
- Check current shipment status
- Refer to state machine above for allowed transitions
- Cannot transition backward except FAILED_DELIVERY → OUT_FOR_DELIVERY

### "Order service notification failed"
- Check order_service is running
- Check ORDER_SERVICE_URL configuration
- Check X-Internal-Service-Key match between services
- This will NOT fail shipment creation (logged as warning only)

---

## Useful Commands

### Run Tests
```bash
python manage.py test modules.shipping.tests
```

### Create Superuser (for Admin)
```bash
python manage.py createsuperuser
```

### Check Migrations
```bash
python manage.py showmigrations modules.shipping
```

### Run Migrations
```bash
python manage.py migrate modules.shipping
```

### Shell Access
```bash
python manage.py shell

# In shell:
from modules.shipping.infrastructure.models import ShipmentModel
shipment = ShipmentModel.objects.first()
print(shipment.shipment_reference)
```

---

## Example Workflow

```bash
# 1. Check health
curl http://localhost:8006/health/

# 2. Create shipment
RESPONSE=$(curl -X POST http://localhost:8006/api/v1/internal/shipments/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: dev-key-change-in-production" \
  -d '{ ... }')

# Extract shipment_reference
SHIPMENT_REF=$(echo $RESPONSE | jq -r '.data.shipment_reference')

# 3. Check tracking (public)
curl http://localhost:8006/api/v1/shipments/$SHIPMENT_REF/tracking/

# 4. Mark picked up (internal)
curl -X POST http://localhost:8006/api/v1/internal/shipments/$SHIPMENT_REF/mark-picked-up/ \
  -H "X-Internal-Service-Key: dev-key-change-in-production"

# 5. Auto-advance to delivered (mock)
curl -X POST http://localhost:8006/api/v1/mock-shipments/$SHIPMENT_REF/advance/ \
  -H "Content-Type: application/json" \
  -H "X-Mock-Enabled: true" \
  -d '{"target_status": "DELIVERED"}'

# 6. Check final status
curl http://localhost:8006/api/v1/shipments/$SHIPMENT_REF/status/
```

---

**For more details, see README_SHIPPING.md**
