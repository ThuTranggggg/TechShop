# Inventory Service

A production-ready microservice for managing stock levels, reservations, and inventory operations in the TechShop e-commerce platform. Built with Django REST Framework following Domain-Driven Design (DDD) principles.

## 📋 Table of Contents

- [Purpose & Vision](#purpose--vision)
- [Domain Scope](#domain-scope)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
- [Database Models](#database-models)
- [API Endpoints](#api-endpoints)
- [Setup & Development](#setup--development)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Admin Interface](#admin-interface)
- [Assumptions & Limitations](#assumptions--limitations)
- [Future Enhancements](#future-enhancements)

## Purpose & Vision

The Inventory Service is a bounded context that owns:
- **Stock levels** (on-hand, reserved, available quantities)
- **Reservations** (temporary stock holds for shopping carts and orders)
- **Movements** (audit trail of all stock changes)
- **Warehouse locations** (basic warehouse management)

What the Inventory Service **does NOT own**:
- Product details (name, description, category, price) → managed by `product_service`
- Order fulfillment logic → managed by `order_service`
- Payment processing → managed by `payment_service`
- Shipping operations → managed by `shipping_service`

## Domain Scope

### Bounded Context

The Inventory context operates independently with its own database and maintains references to external services via IDs only (no embedding of full domain objects).

**Key Principle**: Inventory only holds references to products via `product_id` and `variant_id`, never embedding full product data.

### Core Responsibilities

1. **Stock Item Management**
   - Track inventory for products/variants per warehouse
   - Enforce stock level constraints
   - Monitor low stock conditions

2. **Reservation Management**
   - Create temporary stock reservations for carts/orders
   - Manage reservation lifecycle (active → confirmed/released/expired/cancelled)
   - Prevent over-reservations

3. **Stock Operations**
   - Stock in (receive goods)
   - Stock out (remove goods)
   - Adjustments (corrections and transfers)

4. **Audit & Traceability**
   - Complete movement history
   - Reference tracking to orders, purchase orders, etc.

## Architecture

### DDD Layered Architecture

```
presentation/          → API Views, Serializers, Permissions
    ↓
application/           → Use Cases, Application Services, DTOs
    ↓
domain/               → Entities, Value Objects, Domain Services, Repositories
    ↓
infrastructure/       → Django Models, ORM Repositories, Querysets
```

### Directory Structure

```
modules/inventory/
├── domain/
│   ├── entities.py           # StockItem, StockReservation, StockMovement
│   ├── value_objects.py      # Quantity, ProductReference, StockStatus
│   ├── enums.py              # ReservationStatus, StockMovementType
│   ├── services.py           # InventoryDomainService
│   └── repositories.py       # Repository interfaces (ABC)
├── application/
│   ├── services.py           # InventoryApplicationService (use cases)
│   └── dtos.py              # Data Transfer Objects
├── infrastructure/
│   ├── models.py            # Django ORM models
│   └── repositories.py      # Repository implementations
├── presentation/
│   ├── api.py               # ViewSets and API views
│   ├── serializers.py       # DRF Serializers
│   └── permissions.py       # Custom permissions
├── management/
│   └── commands/
│       └── seed_inventory.py # Seed data command
├── admin.py                 # Django admin configuration
├── apps.py                  # App config
└── urls.py                  # URL routing
```

## Core Concepts

### Stock Item (Aggregate Root)

An inventory record for a product/variant at a specific warehouse.

**Properties:**
- `id`: UUID (unique identifier)
- `product_id`: UUID (from product_service)
- `variant_id`: UUID (nullable if product has no variants)
- `sku`: String (optional SKU from product)
- `warehouse_code`: String (warehouse location)
- `on_hand_quantity`: Integer (actual stock)
- `reserved_quantity`: Integer (in active reservations)
- `available_quantity`: Computed (on_hand - reserved)
- `safety_stock`: Integer (low-stock threshold)
- `is_active`: Boolean

**Business Rules:**
```
available_quantity = on_hand_quantity - reserved_quantity
reserved_quantity ≤ on_hand_quantity
on_hand_quantity ≥ 0
unique(product_id, variant_id, warehouse_code)
```

### Stock Reservation

A temporary hold on stock for a shopping cart or order.

**Lifecycle:**
```
ACTIVE ──→ CONFIRMED (payment success)
   ├──→ RELEASED (order cancelled)
   ├──→ CANCELLED (manual cancel)
   └──→ EXPIRED (timeout)
```

**Properties:**
- `id`: UUID
- `reservation_code`: String (unique, idempotent)
- `status`: Enum (active, confirmed, released, expired, cancelled)
- `quantity`: Integer
- `expires_at`: DateTime (expiration time)
- `order_id`, `cart_id`: Optional references

### Stock Movement

Immutable audit record of every stock change.

**Movement Types:**
- `stock_in` - Received goods
- `stock_out` - Removed goods
- `reservation_created` - Reservation placed
- `reservation_released` - Reservation released
- `reservation_confirmed` - Reservation confirmed (stock committed)
- `adjustment_increase` - Added via adjustment
- `adjustment_decrease` - Removed via adjustment
- `correction` - Inventory correction

## Database Models

### StockItemModel

```sql
CREATE TABLE stock_items (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL,
    variant_id UUID,
    sku VARCHAR(100),
    warehouse_code VARCHAR(50) NOT NULL,
    on_hand_quantity BIGINT NOT NULL DEFAULT 0,
    reserved_quantity BIGINT NOT NULL DEFAULT 0,
    safety_stock BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (product_id, variant_id, warehouse_code) WHERE is_active = TRUE,
    CHECK (on_hand_quantity >= 0),
    CHECK (reserved_quantity >= 0),
    CHECK (reserved_quantity <= on_hand_quantity)
);
```

### StockReservationModel

```sql
CREATE TABLE stock_reservations (
    id UUID PRIMARY KEY,
    reservation_code VARCHAR(100) UNIQUE NOT NULL,
    stock_item_id UUID NOT NULL REFERENCES stock_items,
    product_id UUID NOT NULL,
    variant_id UUID,
    order_id UUID,
    cart_id UUID,
    user_id UUID,
    quantity BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (status, expires_at),
    INDEX (order_id, status)
);
```

### StockMovementModel

```sql
CREATE TABLE stock_movements (
    id UUID PRIMARY KEY,
    stock_item_id UUID NOT NULL REFERENCES stock_items,
    product_id UUID NOT NULL,
    variant_id UUID,
    movement_type VARCHAR(30) NOT NULL,
    quantity BIGINT NOT NULL,
    reference_type VARCHAR(30),
    reference_id VARCHAR(100),
    note TEXT,
    created_by UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP,
    INDEX (stock_item_id, created_at),
    INDEX (movement_type, created_at),
    INDEX (reference_type, reference_id)
);
```

## API Endpoints

### Admin/Staff Endpoints (requires `X-Admin: true` header)

**Stock Item Management:**
- `GET /api/v1/admin/inventory/stock-items/` - List stock items
- `POST /api/v1/admin/inventory/stock-items/` - Create stock item
- `GET /api/v1/admin/inventory/stock-items/{id}/` - Get stock item
- `PATCH /api/v1/admin/inventory/stock-items/{id}/` - Update stock item
- `POST /api/v1/admin/inventory/stock-items/{id}/stock-in/` - Process stock in
- `POST /api/v1/admin/inventory/stock-items/{id}/stock-out/` - Process stock out
- `POST /api/v1/admin/inventory/stock-items/{id}/adjust/` - Adjust stock
- `GET /api/v1/admin/inventory/stock-items/{id}/movements/` - Get movements

### Internal/Service-to-Service APIs (requires `X-Internal-Service-Key` header)

**Availability & Reservation:**
- `POST /api/v1/internal/inventory/check-availability/` - Check availability for items
- `POST /api/v1/internal/inventory/reservations/` - Create reservation
- `GET /api/v1/internal/inventory/products/{product_id}/availability/` - Get product availability
- `GET /api/v1/internal/inventory/variants/{variant_id}/availability/` - Get variant availability

### Response Format

**Success:**
```json
{
  "success": true,
  "message": "OK",
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Error message",
  "errors": { ...details }
}
```

## Setup & Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for async tasks)

### Installation

1. **Clone and navigate to service:**
```bash
cd services/inventory_service
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run migrations:**
```bash
python manage.py migrate
```

5. **Seed sample data:**
```bash
python manage.py seed_inventory
```

6. **Create superuser (for admin):**
```bash
python manage.py createsuperuser
```

7. **Start development server:**
```bash
python manage.py runserver 0.0.0.0:8007
```

### Environment Variables

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=inventory_service
DB_USER=inventory_service
DB_PASSWORD=inventory_service_password
DB_HOST=localhost
DB_PORT=5432

# Service
SERVICE_NAME=inventory_service
SERVICE_PORT=8007

# Auth (Internal Services)
INTERNAL_SERVICE_KEY=your-internal-service-key

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

### Docker Compose

```bash
docker-compose up inventory_service inventory_service_db
```

## Usage Examples

### 1. Create Stock Item

```bash
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "product_id": "12345678-1234-5678-1234-567812345678",
    "variant_id": "22345678-1234-5678-1234-567812345678",
    "sku": "SGS24-256-BLK",
    "warehouse_code": "MAIN",
    "on_hand_quantity": 100,
    "safety_stock": 10
  }'
```

### 2. Check Availability (Internal API)

```bash
curl -X POST http://localhost:8007/api/v1/internal/inventory/check-availability/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: your-internal-service-key" \
  -d '{
    "items": [
      {
        "product_id": "12345678-1234-5678-1234-567812345678",
        "variant_id": "22345678-1234-5678-1234-567812345678",
        "quantity": 2
      }
    ]
  }'
```

Response:
```json
{
  "success": true,
  "message": "Availability checked",
  "data": {
    "items": [
      {
        "product_id": "12345678-1234-5678-1234-567812345678",
        "variant_id": "22345678-1234-5678-1234-567812345678",
        "requested_quantity": 2,
        "available_quantity": 95,
        "can_reserve": true,
        "is_in_stock": true,
        "stock_item_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      }
    ]
  }
}
```

### 3. Create Reservation

```bash
curl -X POST http://localhost:8007/api/v1/internal/inventory/reservations/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: your-internal-service-key" \
  -d '{
    "product_id": "12345678-1234-5678-1234-567812345678",
    "variant_id": "22345678-1234-5678-1234-567812345678",
    "quantity": 2,
    "order_id": "order-uuid-here",
    "user_id": "user-uuid-here",
    "expires_in_minutes": 60
  }'
```

### 4. Stock In (Admin)

```bash
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/stock-in/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "quantity": 50,
    "reference_id": "PO-12345",
    "note": "Received from supplier ABC"
  }'
```

## Testing

### Run Tests

```bash
# All tests
python manage.py test tests/

# Specific test class
python manage.py test tests.test_inventory.StockItemAggregateTests

# With verbosity
python manage.py test tests/ -v 2

# With coverage
pip install coverage
coverage run --source='.' manage.py test tests/
coverage report
coverage html
```

### Test Structure

- **Domain Tests**: ValidateQuantity, StockStatus, StockItem entities
- **Integration Tests**: Django ORM models and constraints
- **API Tests**: Endpoints, permissions, serialization

## Admin Interface

Access Django admin at `http://localhost:8007/admin/`

Features:
- Browse and filter stock items by product, warehouse, active status
- View and search reservations
- Immutable view of movement history (audit trail)
- Warehouse management

## Assumptions & Limitations

### Current Assumptions

1. **Single Warehouse as Default**
   - Service defaults to "MAIN" warehouse for availability checks
   - No complex multi-warehouse allocation yet
   - Warehouse codes are simple strings (not UUIDs)

2. **Internal Service Authentication**
   - Uses simple header-based key (`X-Internal-Service-Key`)
   - Not production-grade security
   - Should be replaced with OAuth2/JWT in production

3. **Product Service Integration**
   - Takes product_id and variant_id directly from requests
   - Doesn't validate against product_service directly
   - Future: Should fetch product details from product_service API

4. **Reservation Expiry**
   - Expiry is checked at query time (no background job)
   - Active task to expire old reservations should be scheduled

5. **Idempotency**
   - Reservation code helps with idempotency
   - Full idempotent request handling not implemented yet

### Known Limitations

1. **No Real-Time Stock Sync**
   - Stock levels are eventual consistent
   - No distributed locking for concurrent operations
   - Consider Redis-based locking for high concurrency

2. **No Event Publishing**
   - Stock changes are not published as events
   - Other services are not notified of stock changes
   - Should integrate with event broker (Kafka, RabbitMQ) later

3. **No Partial Reservation**
   - Reservation is all-or-nothing (no backorder logic)

4. **Limited Warehouse Features**
   - No warehouse hierarchies
   - No retail location management
   - No 3PL integration

## Future Enhancements

### Phase 2 (Q2 2026)

- [ ] Multi-warehouse allocation strategies
- [ ] Event-driven reservation expiration (Celery task)
- [ ] Redis-based distributed locking for concurrent operations
- [ ] Event publishing to message broker (Kafka/RabbitMQ)
- [ ] Inventory reconciliation job
- [ ] Real-time stock monitoring and alerts
- [ ] Batch import/export of inventory

### Phase 3 (Q3 2026)

- [ ] Advanced warehouse management
- [ ] Transfer orders between warehouses
- [ ] Supplier integration
- [ ] Inventory forecasting with ML
- [ ] Pick & pack workflow
- [ ] Barcode scanning support
- [ ] Physical inventory audit tools

### Phase 4 (Q4 2026)

- [ ] 3PL (Third-Party Logistics) integration
- [ ] International warehouse support
- [ ] Cross-dock operations
- [ ] Inventory aging analysis
- [ ] Supply chain optimization
- [ ] Real-time fulfillment optimization

## Key Files Reference

- `domain/entities.py` - Core business logic (StockItem, StockReservation, StockMovement)
- `application/services.py` - Use case implementations
- `infrastructure/models.py` - Django ORM models
- `presentation/api.py` - API endpoints
- `presentation/permissions.py` - Access control
- `admin.py` - Django admin configuration
- `management/commands/seed_inventory.py` - Data seeding

## Related Services

- **Product Service** - Provides product/variant details
- **Order Service** - Consumes reservation APIs
- **Cart Service** - Checks availability and creates reservations
- **Payment Service** - Triggers reservation confirmation
- **Shipping Service** - Accesses confirmed inventory

## Support & Troubleshooting

### Check Service Health

```bash
curl http://localhost:8007/health/
curl http://localhost:8007/ready/
```

### View API Schema

```
http://localhost:8007/api/schema/
http://localhost:8007/api/docs/
```

### Database Migrations

```bash
# Show migration status
python manage.py showmigrations

# Create new migration
python manage.py makemigrations modules.inventory

# Apply migrations
python manage.py migrate modules.inventory

# Rollback
python manage.py migrate modules.inventory 0001
```

### Common Issues

**"Stock not found" when checking availability:**
- Ensure stock item was created in correct warehouse
- Check product_id matches between services

**"Cannot reserve - insufficient stock":**
- Verify available_quantity is sufficient
- Check for active reservations consuming stock

**Reservation not expiring:**
- Run management command: `python manage.py expire_reservations` (to be created)
- Or it will auto-expire on next query

## License

Part of TechShop e-commerce platform.
