# Order Service

**Order Service** quản lý đơn hàng từ checkout đến delivery. Đây là service quan trọng nhất trong flow purchase.

## Overview

Order Service chuyên trách:
- ✅ Tạo đơn hàng từ cart checkout payload
- ✅ Quản lý order lifecycle & state machine
- ✅ Orchestrate stock reservation → inventory_service
- ✅ Orchestrate payment creation → payment_service
- ✅ Orchestrate shipment → shipping_service
- ✅ Lưu snapshot order tại thời điểm đặt
- ✅ Cung cấp order history & detail cho user & admin

**Không** sở hữu:
- ❌ Product domain (only snapshot)
- ❌ Inventory domain (only orchestrate)
- ❌ Payment logic (only coordination)
- ❌ Shipment logistics (only coordination)

## Architecture

```
modules/order/
├── domain/             # Business logic
├── application/        # Use cases
├── infrastructure/     # ORM, clients, persistence
├── presentation/       # API views & serializers
├── management/         # Commands (seed, etc.)
└── tests/             # Test suite
```

**Key Files:**
- [modules/order/README.md](modules/order/README.md) - Full documentation
- [modules/order/domain/entities.py](modules/order/domain/entities.py) - Order & OrderItem
- [modules/order/domain/enums.py](modules/order/domain/enums.py) - Status enumerations
- [modules/order/domain/services.py](modules/order/domain/services.py) - State machine & validation
- [modules/order/application/services.py](modules/order/application/services.py) - Use cases
- [modules/order/presentation/api.py](modules/order/presentation/api.py) - API endpoints

## Quick Start

### 1. Setup Environment

```bash
# Copy env template
cp .env.example .env

# Edit .env with your database credentials
DB_HOST=order_service_db
DB_USER=order_service
DB_PASSWORD=order_service_password
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Seed Demo Data (Optional)

```bash
python manage.py seed_orders --count=10
```

### 5. Start Server

```bash
# Development
python manage.py runserver 0.0.0.0:8004

# Production
gunicorn config.wsgi:application --bind 0.0.0.0:8004
```

### 6. Verify

```bash
# Health check
curl http://localhost:8004/health/

# API docs
curl http://localhost:8004/api/docs/

# Create order (requires cart_id, etc.)
curl -X POST http://localhost:8004/api/v1/orders/from-cart/ \
  -H "X-User-ID: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_id": "...",
    "shipping_address": {...}
  }'
```

## API Quick Reference

### Public Endpoints

```bash
# List user's orders
GET /api/v1/orders/
  Header: X-User-ID: {user_id}

# Get order detail
GET /api/v1/orders/{order_id}/
  Header: X-User-ID: {user_id}

# Create order from cart
POST /api/v1/orders/from-cart/
  Header: X-User-ID: {user_id}
  Body: {
    "cart_id": "...",
    "shipping_address": {...},
    "notes": "..." (optional)
  }

# Cancel order
POST /api/v1/orders/{order_id}/cancel/
  Header: X-User-ID: {user_id}
  Body: { "reason": "..." }

# Get order timeline
GET /api/v1/orders/{order_id}/timeline/
  Header: X-User-ID: {user_id}

# Get order status
GET /api/v1/orders/{order_id}/status/
  Header: X-User-ID: {user_id}
```

### Internal Endpoints (Service-to-Service)

```bash
# Create order (called by internal services)
POST /api/v1/internal/orders/create-from-cart/
  Header: X-Internal-Service-Key: {key}

# Payment success callback
POST /api/v1/internal/orders/{order_id}/payment-success/
  Header: X-Internal-Service-Key: {key}
  Body: { "payment_id": "..." }

# Payment failure callback
POST /api/v1/internal/orders/{order_id}/payment-failed/
  Header: X-Internal-Service-Key: {key}
  Body: { "reason": "..." }

# Get order (internal)
GET /api/v1/internal/orders/{order_id}/
  Header: X-Internal-Service-Key: {key}
```

## Status Lifecycle

```
pending
  ↓
awaiting_payment (stock reserved, waiting for payment)
  ├→ paid (payment success)
  └→ payment_failed (payment failure)

paid
  ↓
processing (stock confirmed, preparing shipment)
  ↓
shipping (shipment created)
  ↓
delivered (delivery confirmed)
  ↓
completed (final state)

Any state → cancelled (with restrictions)
```

## Environment Variables

```bash
# Service Config
SERVICE_NAME=order_service
SERVICE_PORT=8004
DEBUG=true

# Database
DB_HOST=order_service_db
DB_PORT=5432
DB_NAME=order_service
DB_USER=order_service
DB_PASSWORD=order_service_password

# Inter-service URLs
CART_SERVICE_URL=http://cart_service:8003
INVENTORY_SERVICE_URL=http://inventory_service:8007
PAYMENT_SERVICE_URL=http://payment_service:8005
SHIPPING_SERVICE_URL=http://shipping_service:8006

# Security
INTERNAL_SERVICE_KEY=your-internal-key
SECRET_KEY=your-secret-key

# Other
UPSTREAM_TIMEOUT=5
CORS_ALLOW_ALL_ORIGINS=true
TIME_ZONE=UTC
LOG_LEVEL=INFO
```

## Running Tests

```bash
# Run all tests
python manage.py test modules.order.tests

# Run with coverage
coverage run --source='modules.order' manage.py test modules.order.tests
coverage report

# Run specific test class
python manage.py test modules.order.tests.test_order_service.OrderEntityTests

# Verbosity
python manage.py test modules.order.tests --verbosity=2
```

## Admin Panel

```
URL: http://localhost:8004/admin/

Models:
- Order
- OrderItem
- OrderStatusHistory

Filters: status, payment_status, fulfillment_status, created_at, placed_at
Search: order_number, user_id, email, payment_reference
```

## Docker

```bash
# Build
docker build -t order_service .

# Run
docker run -p 8004:8004 \
  --env-file .env \
  --link order_service_db:order_service_db \
  order_service

# Docker Compose (if using)
docker-compose up order_service
```

## Database Schema

### OrderModel
- id (UUID, PK)
- order_number (VARCHAR, unique)
- user_id (UUID, FK to user_service)
- cart_id (UUID, reference only)
- status, payment_status, fulfillment_status (VARCHAR)
- pricing fields (subtotal, shipping, discount, tax, grand_total)
- snapshots (customer name/email/phone, shipping address)
- references (payment_id, shipment_id, stock_reservation_refs)
- milestones (placed_at, paid_at, cancelled_at, completed_at)
- timestamps (created_at, updated_at)

### OrderItemModel
- id (UUID, PK)
- order_id (UUID, FK to OrderModel)
- product_reference (product_id, variant_id, sku)
- product_snapshot (name, slug, brand, category, etc.)
- pricing (quantity, unit_price, line_total)
- attributes (JSON)
- timestamps

### OrderStatusHistoryModel
- id (UUID, PK)
- order_id (UUID, FK)
- from_status, to_status (VARCHAR)
- note, changed_by (optional)
- metadata (JSON)
- created_at

## Inter-Service Integration

### Cart Service Integration
- GET `/internal/carts/{id}/validate/` - Validate cart
- POST `/internal/carts/{id}/checkout-payload/` - Build payload
- POST `/internal/carts/{id}/mark-checked-out/` - Mark as checked out

### Inventory Service Integration
- POST `/internal/inventory/reserve/` - Reserve stock
- POST `/internal/inventory/confirm/` - Confirm reservation
- POST `/internal/inventory/release/` - Release reservation

### Payment Service Integration
- POST `/internal/payments/create/` - Create payment
- POST `/internal/orders/{id}/payment-success/` (callback)
- POST `/internal/orders/{id}/payment-failed/` (callback)

### Shipping Service Integration (Future)
- POST `/internal/shipments/create/` - Create shipment
- POST `/internal/orders/{id}/shipment-created/` (callback)

## Development Workflow

### 1. Implement Feature

```bash
# Create model/migration
python manage.py makemigrations modules.order

# Write tests first (TDD)
# vim modules/order/tests/test_*.py

# Implement business logic
# vim modules/order/domain/*.py
# vim modules/order/application/services.py

# Implement API
# vim modules/order/presentation/api.py
# vim modules/order/presentation/serializers.py
```

### 2. Test Locally

```bash
# Run tests
python manage.py test modules.order.tests

# Manual testing
curl -v http://localhost:8004/api/v1/orders/
```

### 3. Check Code Quality

```bash
# Linting (flake8, black)
flake8 modules/order
black modules/order

# Type checking (mypy)
mypy modules/order
```

## Troubleshooting

### Migration Issues

```bash
# Check status
python manage.py showmigrations modules.order

# Rollback
python manage.py migrate modules.order 0000_previous

# Fresh start
python manage.py migrate modules.order zero
python manage.py migrate modules.order
```

### Order Creation Fails

```
Check:
1. Cart service is running
2. Stock is available
3. Payment service is responding
4. Network connectivity between services
5. Check logs: python manage.py runserver with DEBUG=true
```

### Permission Denied on API

```
Check:
1. X-User-ID header is provided
2. X-Internal-Service-Key matches for internal endpoints
3. User owns the order (for GET/POST endpoints)
```

## Performance Tips

- Indexes on order_number, user_id, status, created_at
- Batch order retrieval with select_related
- Cache order detail for read-heavy scenarios
- Consider Redis cache for payment status checks

## Security Considerations

- X-User-ID header validation (from gateway)
- X-Internal-Service-Key for service-to-service
- CSRF protection via Django middleware
- SQL injection prevention (ORM)
- Rate limiting (configure in gateway)
- HTTPS in production

## Related Documentation

- **Full Documentation**: [modules/order/README.md](modules/order/README.md)
- **Domain Model Details**: Order, OrderItem, OrderStatusHistory entities
- **State Machine**: OrderStatus, PaymentStatus, FulfillmentStatus enums
- **Business Rules**: OrderValidator, OrderStateTransitionService
- **Use Cases**: CreateOrderFromCart, HandlePaymentSuccess, CancelOrder

## Support & Debugging

```bash
# Enable verbose logging
LOG_LEVEL=DEBUG python manage.py runserver

# Check migrations
python manage.py showmigrations

# Database inspection
python manage.py dbshell
SELECT COUNT(*) FROM order_ordermodel;
SELECT * FROM order_ordermodel LIMIT 1;

# Check admin
http://localhost:8004/admin/
Login: admin / admin (if created)
```

## Next Steps

1. ✅ Implement order_service
2. ⏳ Implement payment_service (if not done)
3. ⏳ Implement shipping_service (if not done)
4. ⏳ Integrate full checkout flow
5. ⏳ Add refund & return workflows
6. ⏳ Add analytics & reporting

## License

Same as monorepo.

---

📚 **More Info**: See [modules/order/README.md](modules/order/README.md) for comprehensive documentation.

- `modules/order/application`: commands, queries, application services
- `modules/order/infrastructure`: ORM models, repository implementations, querysets
- `modules/order/presentation`: API serializers/views/controllers
