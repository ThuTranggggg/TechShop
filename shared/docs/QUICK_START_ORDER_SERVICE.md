# Quick Start: Order Service

**Order Service** is fully implemented with DDD architecture. This guide gets you up and running in 10 minutes.

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL running (or Docker)
- Git
- Virtual environment

## ⚡ 5-Minute Setup

### 1. Environment Setup

```bash
# Navigate to order_service
cd services/order_service

# Copy environment template
cp .env.example .env

# Edit .env (or use defaults for dev)
# DB_HOST=localhost, DB_USER=order_service, etc.
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create & Migrate Database

```bash
# Create database (if using PostgreSQL)
createdb order_service

# Run migrations
python manage.py migrate
```

### 4. Seed Demo Data

```bash
# Create 10 sample orders in various states
python manage.py seed_orders --count=10
```

### 5. Start Server

```bash
python manage.py runserver 0.0.0.0:8004
```

✅ **Ready!** Server running at `http://localhost:8004`

---

## 🧪 Quick Verification

### Health Check
```bash
curl http://localhost:8004/health/
# Response: {"status": "ok", "timestamp": "2024-01-01T00:00:00Z"}
```

### API Documentation
```
Open in browser: http://localhost:8004/api/docs/
```

### Admin Panel
```
Open in browser: http://localhost:8004/admin/
Username: admin
Password: admin (use createsuperuser to set)
```

### Create Admin User
```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

---

## 📝 Quick API Test

### List User's Orders
```bash
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/
```

### Get Order Detail
```bash
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/{order_id}/
```

### Create Order from Cart
```bash
curl -X POST http://localhost:8004/api/v1/orders/from-cart/ \
  -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_id": "your-cart-id",
    "shipping_address": {
      "receiver_name": "John Doe",
      "receiver_phone": "+84912345678",
      "line1": "123 Main St",
      "line2": "Apt 4B",
      "ward": "Ward 1",
      "district": "District 1",
      "city": "Ho Chi Minh City",
      "country": "Vietnam",
      "postal_code": "70000"
    }
  }'
```

### Cancel Order
```bash
curl -X POST http://localhost:8004/api/v1/orders/{order_id}/cancel/ \
  -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Changed my mind"}'
```

---

## 🧪 Run Tests

### All Tests
```bash
python manage.py test modules.order.tests -v 2
```

### Specific Test Class
```bash
python manage.py test modules.order.tests.test_order_service.OrderEntityTests
```

### With Coverage
```bash
coverage run --source='modules.order' manage.py test modules.order.tests
coverage report
```

---

## 📦 Docker (Optional)

### Build Image
```bash
docker build -t order_service:latest .
```

### Run Container
```bash
docker run -p 8004:8004 \
  --env-file .env \
  -e DB_HOST=host.docker.internal \
  order_service
```

### Docker Compose
```bash
# From monorepo root
docker-compose up order_service
```

---

## 🔍 Key Files

| File | Purpose |
|------|---------|
| [modules/order/domain/entities.py](services/order_service/modules/order/domain/entities.py) | Order & OrderItem aggregate |
| [modules/order/domain/enums.py](services/order_service/modules/order/domain/enums.py) | Status enumerations |
| [modules/order/application/services.py](services/order_service/modules/order/application/services.py) | Use case implementations |
| [modules/order/presentation/api.py](services/order_service/modules/order/presentation/api.py) | REST API endpoints |
| [modules/order/infrastructure/models.py](services/order_service/modules/order/infrastructure/models.py) | Django ORM models |
| [modules/order/README.md](services/order_service/modules/order/README.md) | Full documentation |

---

## 🚀 Next Steps

1. **Explore Admin**: Visit http://localhost:8004/admin/
2. **Read Full Docs**: [modules/order/README.md](services/order_service/modules/order/README.md)
3. **Integrate with Other Services**: Cart, Inventory, Payment, Shipping
4. **Run End-to-End Tests**: Test full checkout flow

---

## ❓ Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
psql -U postgres -d postgres -c "SELECT 1"

# Create database if missing
createdb order_service

# Or use SQLite for dev (edit settings.py)
```

### Migration Error
```bash
# Show migration status
python manage.py showmigrations modules.order

# Rollback and retry
python manage.py migrate modules.order zero
python manage.py migrate modules.order
```

### Permission Denied (API)
```bash
# Ensure X-User-ID header is provided
# Headers must include: X-User-ID: {valid-uuid}
```

### Inter-Service Connection Error
```bash
# Check service URLs in .env
CART_SERVICE_URL=http://localhost:8003
INVENTORY_SERVICE_URL=http://localhost:8007
PAYMENT_SERVICE_URL=http://localhost:8005
SHIPPING_SERVICE_URL=http://localhost:8008
```

---

## 📚 Documentation Map

- **This File**: Quick start (5 min)
- **[README.md](services/order_service/README.md)**: Quick reference
- **[modules/order/README.md](services/order_service/modules/order/README.md)**: Full documentation (40+ sections)
- **Domain Model**: [entities.py](services/order_service/modules/order/domain/entities.py)
- **State Machine**: [enums.py](services/order_service/modules/order/domain/enums.py)
- **Use Cases**: [application/services.py](services/order_service/modules/order/application/services.py)
- **API Endpoints**: [presentation/api.py](services/order_service/modules/order/presentation/api.py)

---

## 💡 Pro Tips

- Use `--count=20` with seed_orders for more test data
- Enable `DEBUG=true` in .env for detailed error messages
- Check `LOG_LEVEL=DEBUG` for verbose logging
- Use admin panel to inspect orders, items, and status history
- Run tests before deployment: `python manage.py test modules.order.tests`

---

**Ready to dig deeper?** → Read [modules/order/README.md](services/order_service/modules/order/README.md)

**Questions?** → Check troubleshooting section or review test examples in [test_order_service.py](services/order_service/modules/order/tests/test_order_service.py)
