# inventory_service

A production-ready microservice for inventory and stock management in the TechShop e-commerce platform.

## Overview

The Inventory Service is a bounded context (following DDD principles) that manages:
- **Stock levels** across warehouses
- **Reservations** for shopping carts and orders
- **Stock operations** (receive, dispense, adjust)
- **Audit trail** of all inventory changes

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Seed sample data
python manage.py seed_inventory

# Start development server
python manage.py runserver 0.0.0.0:8007
```

### 2. Access Services

- **API**: http://localhost:8007/api/v1/
- **Admin**: http://localhost:8007/admin/
- **Docs**: http://localhost:8007/api/docs/
- **Health**: http://localhost:8007/health/

### 3. Create Stock Item (Admin)

```bash
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "product_id": "12345678-1234-5678-1234-567812345678",
    "warehouse_code": "MAIN",
    "on_hand_quantity": 100
  }'
```

### 4. Check Availability (Internal API)

```bash
curl -X POST http://localhost:8007/api/v1/internal/inventory/check-availability/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: test-key" \
  -d '{
    "items": [
      {
        "product_id": "12345678-1234-5678-1234-567812345678",
        "quantity": 2
      }
    ]
  }'
```

## Architecture

Built with **Django + REST Framework** following **DDD (Domain-Driven Design)**:

```
presentation/     → API Views, Serializers, Permissions
application/      → Use Cases, Application Services
domain/          → Entities, Value Objects, Domain Services
infrastructure/  → Django Models, Repositories
```

## Key Features

✅ **DDD Layer Separation** - Clean architecture with isolated concerns
✅ **Stock Item Management** - Track inventory per product/variant/warehouse
✅ **Reservation System** - Temporary stock holds with expiry
✅ **Movement Audit Trail** - Complete history of all changes
✅ **Admin Interface** - Full Django admin with filtering and search
✅ **Comprehensive Tests** - Domain, integration, and API tests
✅ **Seed Data** - Management command for demo data
✅ **API Documentation** - OpenAPI/Swagger docs

## Models

### StockItemModel
- Tracks on_hand, reserved, and available quantities
- Per product/variant/warehouse
- Enforces business rule constraints

### StockReservationModel
- Temporary holds for carts and orders
- State machine: active → confirmed/released/expired/cancelled
- Auto-expiry tracking

### StockMovementModel
- Immutable audit trail
- Records all stock changes with reason
- Tracks references (order_id, purchase_order_id, etc.)

### WarehouseModel
- Optional warehouse master data
- Supports future multi-warehouse operations

## API Endpoints

### Admin (requires `X-Admin: true`)
- `GET /api/v1/admin/inventory/stock-items/` - List
- `POST /api/v1/admin/inventory/stock-items/` - Create
- `GET /api/v1/admin/inventory/stock-items/{id}/` - Get
- `PATCH /api/v1/admin/inventory/stock-items/{id}/` - Update
- `POST /api/v1/admin/inventory/stock-items/{id}/stock-in/` - Stock in
- `POST /api/v1/admin/inventory/stock-items/{id}/stock-out/` - Stock out
- `POST /api/v1/admin/inventory/stock-items/{id}/adjust/` - Adjust stock
- `GET /api/v1/admin/inventory/stock-items/{id}/movements/` - Get movements

### Internal Services (requires `X-Internal-Service-Key`)
- `POST /api/v1/internal/inventory/check-availability/` - Check availability
- `POST /api/v1/internal/inventory/reservations/` - Create reservation
- `GET /api/v1/internal/inventory/products/{product_id}/availability/` - Get product availability

## Testing

```bash
# Run all tests
python manage.py test tests/

# Run specific test
python manage.py test tests.test_inventory.StockItemAggregateTests

# With coverage
coverage run --source='.' manage.py test tests/
coverage report
```

## Admin Interface

Managed Django admin at `/admin/`:
- Browse and filter stock items
- View reservations
- Audit movement history
- Manage warehouses

## Environment Variables

```env
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=inventory_service
DB_USER=inventory_service
DB_PASSWORD=inventory_service_password
DB_HOST=localhost
DB_PORT=5432
INTERNAL_SERVICE_KEY=your-internal-service-key
SERVICE_PORT=8007
```

## Database

PostgreSQL with indexes and check constraints:
- Unique constraint on (product_id, variant_id, warehouse_code)
- Check constraints for non-negative quantities
- Indexes for common queries

## Design Decisions

### Inventory ≠ Product
- Inventory doesn't embed full product data
- Only references product_id and variant_id
- Product details stay in product_service

### Warehouse as Dimension
- Default to "MAIN" warehouse
- Extensible for multi-warehouse later
- Simple string codes, not UUIDs

### Reservation Lifecycle
- Active → Confirmed (payment success)
- Active → Released (cancelled)
- Active → Expired (timeout)
- Can only transition forward

### Audit-First Movement
- Every stock change creates immutable movement record
- Tracks order_id, purchase_order_id for references
- Enables reconciliation and debugging

## Documentation

See [INVENTORY_SERVICE.md](INVENTORY_SERVICE.md) for:
- Detailed architecture and DDD structure
- Complete API reference
- Business rules and constraints
- Future enhancement roadmap
- Troubleshooting guide
- Database schema details

## Related Services

- **Product Service** - Provides product/variant metadata
- **Cart Service** - Checks availability, creates reservations
- **Order Service** - Confirms reservations on order placement
- **Payment Service** - Triggers stock commitment
- **Shipping Service** - Accesses confirmed inventory

## Ports

- Application: `8007`
- Database: `5439` (via docker-compose)

## Next Steps

1. **Run the service** with `python manage.py runserver 0.0.0.0:8007`
2. **Create inventory** via admin API
3. **Check availability** via internal API
4. **Create reservations** when orders are placed
5. **Confirm reservations** when payment succeeds

## Support

Issues? Check the [INVENTORY_SERVICE.md](INVENTORY_SERVICE.md) troubleshooting section.

- `modules/inventory/application`: commands, queries, application services
- `modules/inventory/infrastructure`: ORM models, repository implementations, querysets
- `modules/inventory/presentation`: API serializers/views/controllers
