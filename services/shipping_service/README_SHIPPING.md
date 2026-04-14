# Shipping Service

Complete shipment and delivery lifecycle management for e-commerce.

## Overview

The Shipping Service manages the entire journey of customer orders from creation through delivery, providing:

- **Shipment Lifecycle Management**: Track shipments through 9 distinct states with strict transition rules
- **Multi-Carrier Support**: Pluggable carrier abstraction (with MockShippingProvider for development)
- **Real-time Tracking**: Public tracking API for customers and internal APIs for backend services
- **Event Timeline**: Immutable audit trail of every shipment state change
- **Order Integration**: Bi-directional communication with order_service for status updates
- **Mock Provider**: Full-featured development/testing carrier without external dependencies

## Architecture

### Domain-Driven Design (4-Layer)

```
┌─────────────────────────────────────────┐
│    Presentation Layer (REST API)        │
│  Views, Serializers, Permissions        │
├─────────────────────────────────────────┤
│    Application Layer (Use Cases)        │
│    13 orchestration services            │
├─────────────────────────────────────────┤
│  Infrastructure Layer (Persistence)     │
│  ORM Models, Repositories, Providers    │
└─────────────────────────────────────────┘
  ↓ Delegates to
┌─────────────────────────────────────────┐
│      Domain Layer (Business Logic)      │
│  Entities, Value Objects, Repositories  │
└─────────────────────────────────────────┘
```

### Key Components

#### Domain Layer (`modules/shipping/domain/`)

- **Entities**: `Shipment` (aggregate root), `ShipmentTrackingEvent`
- **Value Objects**: `Money`, `ReceiverAddress`, `TrackingInfo`, `ShippingCost`
- **Repositories**: Abstract interfaces for persistence
- **Domain Services**: Validation, factory creation, state transitions

#### Infrastructure Layer (`modules/shipping/infrastructure/`)

- **Models**: Django ORM persistence layer (ShipmentModel, ShipmentItemModel, ShipmentTrackingEventModel)
- **Repositories**: ORM-based implementations with atomic transactions
- **Providers**: Carrier abstraction (BaseShippingProvider, MockShippingProvider, ShippingProviderFactory)
- **Clients**: OrderServiceClient for service-to-service communication

#### Application Layer (`modules/shipping/application/`)

- **DTOs**: Request/response data transfer objects
- **Services**: 13 use case services orchestrating domain logic and infrastructure
- Separation of concerns: API contracts independent from domain models

#### Presentation Layer (`modules/shipping/presentation/`)

- **ViewSets**: 3 DRF ViewSets with 14+ action endpoints
  - InternalShipmentViewSet: For order_service integration
  - PublicShipmentViewSet: For customer tracking
  - MockShipmentViewSet: For development/testing
- **Serializers**: 11 DRF validators and representers
- **Permissions**: IsInternalService, IsMockServiceEnabled, AllowAny guards

## Shipment State Machine

### States (9 total)

```
CREATED
  ↓
PENDING_PICKUP (awaiting pickup from sender)
  ↓
PICKED_UP (picked from sender)
  ↓
IN_TRANSIT (in carrier network)
  ↓
OUT_FOR_DELIVERY (on delivery vehicle)
  ↓
├→ DELIVERED (successfully delivered)
├→ FAILED_DELIVERY (delivery attempt failed)
└→ RETURNED (returned to sender)

CANCELLED (may transition from CREATED or PENDING_PICKUP only)
```

### Transition Rules

| From | To | Allowed | Notes |
|------|----|---------| -----|
| CREATED | PENDING_PICKUP | ✓ | Initial transition |
| CREATED | CANCELLED | ✓ | Before pickup |
| PENDING_PICKUP | PICKED_UP | ✓ | Normal flow |
| PENDING_PICKUP | CANCELLED | ✓ | Before actual pickup |
| PICKED_UP | IN_TRANSIT | ✓ | In carrier network |
| IN_TRANSIT | OUT_FOR_DELIVERY | ✓ | Out for delivery |
| OUT_FOR_DELIVERY | DELIVERED | ✓ | Final success |
| OUT_FOR_DELIVERY | FAILED_DELIVERY | ✓ | Delivery failed |
| FAILED_DELIVERY | OUT_FOR_DELIVERY | ✓ | Retry delivery |
| DELIVERED | CANCELLED | ✗ | Terminal state |
| CANCELLED | * | ✗ | Terminal state |

### Event Types (9 total)

- CREATED: Shipment created
- PENDING_PICKUP: Awaiting pickup
- PICKED_UP: Picked from sender
- DISPATCHED: In carrier network
- IN_HUB: At distribution hub
- OUT_FOR_DELIVERY: Out for delivery
- DELIVERED: Successfully delivered
- FAILED_DELIVERY: Delivery failed
- RETURNED: Returned to origin

## API Documentation

### Base URL

```
http://localhost:8006/api/v1
```

### Endpoints

#### Internal API (for order_service)

Protected with `IsInternalService` permission. Requires `X-Internal-Service-Key` header.

```bash
# Create shipment
POST /internal/shipments/
Content-Type: application/json
X-Internal-Service-Key: dev-key-change-in-production

{
  "order_id": "order-123",
  "order_number": "ORD-001",
  "user_id": "user-456",
  "receiver_name": "John Doe",
  "receiver_phone": "0912345678",
  "address_line1": "123 Main St",
  "ward": "Ward 1",
  "district": "District 1",
  "city": "Ho Chi Minh",
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

Response (201 Created):
{
  "success": true,
  "data": {
    "id": "uuid",
    "shipment_reference": "SHIP-12345",
    "tracking_number": "TRACK-12345",
    "order_id": "order-123",
    "status": "CREATED",
    "created_at": "2024-01-15T10:30:00Z"
  }
}

# Get shipment detail
GET /internal/shipments/{id}/
X-Internal-Service-Key: dev-key-change-in-production

# Get shipment by reference
GET /internal/shipments/reference/{reference}/
X-Internal-Service-Key: dev-key-change-in-production

# Get shipment by order
GET /internal/shipments/order/{order_id}/
X-Internal-Service-Key: dev-key-change-in-production

# Mark picked up
POST /internal/shipments/{reference}/mark-picked-up/
X-Internal-Service-Key: dev-key-change-in-production

# Mark in transit
POST /internal/shipments/{reference}/mark-in-transit/
X-Internal-Service-Key: dev-key-change-in-production

# Mark out for delivery
POST /internal/shipments/{reference}/mark-out-for-delivery/
X-Internal-Service-Key: dev-key-change-in-production

# Mark delivered
POST /internal/shipments/{reference}/mark-delivered/
X-Internal-Service-Key: dev-key-change-in-production

# Mark failed delivery
POST /internal/shipments/{reference}/mark-failed-delivery/
Content-Type: application/json
X-Internal-Service-Key: dev-key-change-in-production

{
  "failure_reason": "Address not found"
}

# Cancel shipment
POST /internal/shipments/{reference}/cancel/
X-Internal-Service-Key: dev-key-change-in-production
```

#### Public API (for customers)

No authentication required. Publicly accessible.

```bash
# Get shipment detail
GET /shipments/{reference}/

Response (200 OK):
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-12345",
    "tracking_number": "TRACK-12345",
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

# Get shipment status
GET /shipments/{reference}/status/

Response (200 OK):
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-12345",
    "status": "IN_TRANSIT",
    "expected_delivery_date": "2024-01-17",
    "last_update": "2024-01-15T14:30:00Z"
  }
}

# Get tracking timeline
GET /shipments/{reference}/tracking/

Response (200 OK):
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-12345",
    "tracking_number": "TRACK-12345",
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
        "notes": "In transit to destination"
      }
    ]
  }
}
```

#### Mock API (for development/testing)

Protected with `IsMockServiceEnabled` permission. Enabled in DEBUG=True or with `X-Mock-Enabled: true` header.

```bash
# Auto-advance shipment status through state machine
POST /mock-shipments/{reference}/advance/
Content-Type: application/json
X-Mock-Enabled: true

{
  "target_status": "DELIVERED"
}

Response (200 OK):
{
  "success": true,
  "data": {
    "shipment_reference": "SHIP-12345",
    "status": "DELIVERED",
    "message": "Shipment advanced from CREATED to DELIVERED through valid path"
  }
}
```

## Data Models

### Shipment

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| shipment_reference | String | Unique tracking reference (e.g., SHIP-12345) |
| order_id | UUID | Foreign key to order_service |
| user_id | UUID | Customer identifier |
| tracking_number | String | Unique carrier tracking number |
| status | Enum | One of 9 ShipmentStatus values |
| receiver_address | JSON | Snapshot of delivery address (immutable) |
| total_items | Integer | Count of items in shipment |
| total_weight | Decimal | Total weight in kg |
| total_price | Decimal | Total item value |
| service_level | Enum | STANDARD, EXPRESS, OVERNIGHT |
| provider | Enum | MOCK, GHN, GHTK, VIETPOST (pluggable) |
| shipping_fee_amount | Decimal | Shipping cost |
| currency | String | Currency code (VND, USD, etc.) |
| carrier_name | String | Carrier company name |
| carrier_shipment_id | String | Carrier's internal shipment ID |
| carrier_tracking_link | URL | Link to carrier's tracking page |
| expected_delivery_date | Date | Estimated delivery date |
| actual_delivery_date | DateTime | When delivered (null if not yet) |
| failed_delivery_reason | String | Reason if delivery failed |
| is_priority | Boolean | Priority/rush delivery flag |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### ShipmentItem

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| shipment_id | UUID | Foreign key to Shipment |
| product_id | UUID | Product identifier |
| product_name | String | Product name |
| sku | String | Stock keeping unit |
| quantity | Integer | Quantity ordered |
| unit_price | Decimal | Price per unit |
| total_price | Decimal | quantity × unit_price |
| created_at | DateTime | Snapshot creation time |

### ShipmentTrackingEvent

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| shipment_id | UUID | Foreign key to Shipment |
| event_type | Enum | One of 9 ShipmentTrackingEventType |
| status | Enum | Associated ShipmentStatus |
| location | String | Geographic location/hub name |
| timestamp | DateTime | Event time (immutable) |
| notes | String | Optional event details |

## Use Cases (Services)

### 1. CreateShipmentService

Create new shipment for order.

```python
success, error, dto = CreateShipmentService().execute(CreateShipmentRequestDTO(...))
```

- Validates receiver address and items
- Checks for existing active shipment for order
- Calls provider to create carrier shipment
- Creates initial CREATED tracking event
- Persists to database (atomic)
- Notifies order_service
- Returns (success: bool, error: str, shipment_dto: DTO)

### 2. GetShipmentDetailService

Retrieve full shipment details by ID.

```python
dto = GetShipmentDetailService().execute(shipment_id: str) -> ShipmentDetailDTO | None
```

### 3. GetShipmentByReferenceService

Retrieve shipment by shipment_reference.

```python
dto = GetShipmentByReferenceService().execute(shipment_reference: str) -> ShipmentDetailDTO | None
```

### 4. GetShipmentStatusService

Quick status query without full details.

```python
dto = GetShipmentStatusService().execute(shipment_reference: str) -> ShipmentStatusDTO | None
```

### 5. GetShipmentTrackingService

Get public tracking response with event timeline.

```python
dto = GetShipmentTrackingService().execute(shipment_reference: str) -> ShipmentTrackingResponseDTO | None
```

### 6. GetShipmentByOrderService

Retrieve shipment for a specific order.

```python
dto = GetShipmentByOrderService().execute(order_id: str) -> ShipmentDetailDTO | None
```

### 7-11. Mark* Services

Services to transition shipment through states:
- `MarkPickedUpService`
- `MarkInTransitService`
- `MarkOutForDeliveryService`
- `MarkDeliveredService` (with idempotency)
- `MarkFailedDeliveryService`

```python
success, error, dto = MarkPickedUpService().execute(shipment_reference: str)
```

### 12. CancelShipmentService

Cancel active shipment.

```python
success, error, dto = CancelShipmentService().execute(shipment_reference: str)
```

- Only allowed from CREATED or PENDING_PICKUP states
- Creates CANCELLED tracking event
- Notifies order_service

### 13. MockAdvanceShipmentStatusService

Auto-transition shipment to target status through valid path (development/testing only).

```python
success, error, dto = MockAdvanceShipmentStatusService().execute(
    shipment_reference: str, 
    target_status: str
)
```

- Validates target status is terminal or more advanced than current
- Transitions through all intermediate states automatically
- Creates appropriate tracking events for each transition
- Useful for testing without manual endpoint calls

## Database Indexes

Database indexes optimize query performance:

- `shipment_reference` (UNIQUE)
- `tracking_number` (UNIQUE)
- `order_id` (B-tree for lookups)
- `user_id` (B-tree for lookups)
- `status` (B-tree for status filtering)
- `provider` (B-tree for provider filtering)
- `created_at` (B-tree for time-based queries)
- `carrier_shipment_id` (for provider callbacks)
- Composite: `(order_id, status)` for active shipments by order

## Provider Abstraction

### BaseShippingProvider

Interface for carrier integration:

```python
class BaseShippingProvider(ABC):
    def create_shipment(self, shipment_data) -> str:
        """Create shipment with carrier, return carrier_shipment_id"""
        pass
    
    def get_status(self, carrier_shipment_id) -> str:
        """Get current carrier status"""
        pass
    
    def cancel_shipment(self, carrier_shipment_id) -> bool:
        """Cancel shipment with carrier"""
        pass
    
    def parse_callback(self, webhook_data) -> dict:
        """Parse carrier webhook callback"""
        pass
```

### MockShippingProvider

In-memory development provider with:
- Status progression through valid state path
- In-memory store (lost on restart)
- `advance_status()` method for manual testing
- Full lifecycle support without external dependencies

### ShippingProviderFactory

Registry for managing providers:

```python
provider = ShippingProviderFactory.get_provider("mock")  # Gets MockShippingProvider
provider = ShippingProviderFactory.get_provider("ghn")   # Future: Real GHN provider
```

## Order Service Integration

### Notifications

Shipping service notifies order_service via `OrderServiceClient`:

- **shipment_created**: When shipment is created
- **shipment_status_updated**: On status transitions
- **shipment_delivered**: When delivered
- **shipment_failed**: When delivery failed

### URL

```
http://order_service:8003/api/v1/internal/shipments/notify/{type}
```

### Headers

```
X-Internal-Service-Key: dev-key-change-in-production
Content-Type: application/json
```

### Payload Examples

```json
POST /internal/shipments/notify/created
{
  "order_id": "order-123",
  "shipment_id": "uuid",
  "shipment_reference": "SHIP-12345",
  "tracking_number": "TRACK-12345",
  "tracking_url": "http://shipping:8006/shipments/SHIP-12345/tracking"
}

POST /internal/shipments/notify/status_updated
{
  "order_id": "order-123",
  "shipment_id": "uuid",
  "shipment_reference": "SHIP-12345",
  "status": "IN_TRANSIT",
  "location": "Distribution Hub A"
}

POST /internal/shipments/notify/delivered
{
  "order_id": "order-123",
  "shipment_id": "uuid",
  "shipment_reference": "SHIP-12345",
  "delivered_at": "2024-01-15T14:30:00Z"
}

POST /internal/shipments/notify/failed
{
  "order_id": "order-123",
  "shipment_id": "uuid",
  "shipment_reference": "SHIP-12345",
  "failure_reason": "Address not found - returned to sender"
}
```

## Running & Testing

### Start Service

```bash
cd services/shipping_service
python manage.py migrate
python manage.py runserver 0.0.0.0:8006
```

### Run Tests

```bash
python manage.py test modules.shipping.tests
```

### Create Test Data

```bash
# Mock data for testing (seed command to be implemented)
python manage.py seed_shipments --count=10
```

### Check Health

```bash
curl http://localhost:8006/health/
curl http://localhost:8006/ready/
```

### Access Admin

```
http://localhost:8006/admin/
```

- Browse ShipmentModel, ShipmentItemModel, ShipmentTrackingEventModel
- View tracking timeline in admin inline

### API Schema & Docs

```
http://localhost:8006/api/schema/  (JSON schema)
http://localhost:8006/api/docs/    (Swagger UI)
```

## Key Design Decisions

### 1. Shipment as Aggregate Root

`Shipment` is the aggregate root managing `ShipmentTrackingEvent` value objects. This enforces:
- Single entity for consistency
- All state transitions through Shipment
- Timeline events are immutable values, not entities
- Strong consistency within aggregat boundary

### 2. Receiver Address Snapshots

`ReceiverAddress` is immutable snapshot, not FK reference to order address:
- Decouples shipping from future address changes
- Preserves exact delivery location at shipment time
- Simplifies cross-service data isolation
- No cascading issues if order address changes later

### 3. Atomic Transactions

All state modifications use `@transaction.atomic`:
- Guarantees consistency even with concurrent requests
- Database rolls back everything if any operation fails
- Event creation and state update succeed or both fail

### 4. Idempotent Delivered State

`MarkDeliveredService` checks `if status == DELIVERED: return success`:
- Multiple calls to mark delivered don't create duplicate events
- Safe for retried API calls
- Essential for production reliability

### 5. Separate Event Type vs Status

Two related but distinct values:
- **Status**: Current shipment state (9 values)
- **Event Type**: What happened (9 values)
- Allows detailed timeline while status is simplified
- Event types map to status transitions

### 6. Public Tracking Without Auth

`PublicShipmentViewSet` has `AllowAny` permission:
- Customers can track without account
- Uses shipment_reference (not internally guessable)
- Provides good UX without security compromise

### 7. Internal Service Auth

`InternalShipmentViewSet` requires `X-Internal-Service-Key`:
- Simple header-based auth for service-to-service (JWT/OAuth later)
- Enough for MVP with verified services
- Can be enhanced with service mesh mutual TLS

## Limitations & Future Enhancements

### Current Limitations

- One shipment per order (MVP - no partial fulfillment)
- Mock provider uses in-memory store (reset on restart)
- No real carrier integration (GHN, GHTK, VNPost)
- No address validation service
- No SMS/email notifications
- Service-to-service auth is basic

### Planned Enhancements

1. **Real Carrier Integration**
   - GHN (Giao Hàng Nhanh)
   - GHTK (Giao Hàng Tiết Kiệm)
   - VietPost
   - Smart carrier selection and rate shopping

2. **Advanced Features**
   - Multiple shipments per order (partial fulfillment)
   - Pickup scheduling optimization
   - Address validation and autocomplete
   - SMS/email notifications
   - Webhook signature verification for carrier callbacks
   - Async event publishing for real-time updates

3. **Improvements**
   - Label PDF generation
   - Return shipment logistics
   - Insurance options
   - Custom packaging options
   - Service mesh with mTLS for security
   - Distributed tracing (OpenTelemetry)
   - Rate limiting and quotas

## Configuration

### Environment Variables

```bash
# Database
DB_NAME=shipping_service
DB_USER=shipping_service
DB_PASSWORD=shipping_service_password
DB_HOST=shipping_service_db
DB_PORT=5432

# Service
DEBUG=True
SERVICE_NAME=shipping_service
SERVICE_PORT=8006
SECRET_KEY=your-secret-key

# Integration
INTERNAL_SERVICE_KEY=dev-key-change-in-production
ORDER_SERVICE_URL=http://order_service:8003/api/v1/internal

# Feature Flags
ENABLE_REAL_CARRIERS=False
ENABLE_NOTIFICATIONS=True
```

## Support & Troubleshooting

### Common Issues

1. **"Shipment not found" on public tracking**
   - Verify shipment_reference format (SHIP-xxxxx)
   - Check shipment exists in database
   - Public API doesn't require auth but shipment must exist

2. **"Permission denied" on internal endpoints**
   - Verify `X-Internal-Service-Key` header matches config
   - Check service calling has correct key
   - In DEBUG=True, localhost is allowed without key

3. **Order service notifications failing**
   - Check order_service is running (http://order_service:8003/health/)
   - Verify internal service key is configured on order_service
   - Check network connectivity (docker-compose networking)
   - Logs will show warnings but won't fail shipment creation

4. **Tracking events not showing**
   - Events are created on every status transition
   - Check shipment status has been transitioned (not still CREATED)
   - Verify tracking_number exists for public API
   - Use admin to view complete timeline

### Debug Tips

1. Enable verbose logging in settings.py
2. Check admin interface for shipment timeline
3. Use mock endpoints to advance status for testing
4. Review middleware logs for request/response details

## Contact & Support

For issues or questions about the shipping service:

1. Check API documentation above
2. Review test cases for usage examples
3. Check Django admin for current data state
4. Review Git commit history for recent changes

---

**Version**: 0.1.0 (Initial Release)  
**Last Updated**: 2024-01-15  
**Maintainer**: Development Team  
**Status**: Production-Ready (Mock Carrier) ✓
