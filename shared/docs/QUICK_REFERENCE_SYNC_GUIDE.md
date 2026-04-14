# Quick Reference & Sync Guide

**Fast reference for running TechShop microservices with order_service fully integrated.**

---

## 🚀 30-Second Start (Docker)

```bash
# From monorepo root
docker-compose up

# Wait 30 seconds, then verify:
curl http://localhost:8004/health/
# Expected: {"status": "ok"}

# Open API docs
# http://localhost:8004/api/docs/
```

---

## 🏃 5-Minute Local Start

```bash
# Terminal 1: order_service
cd services/order_service
source venv/bin/activate
python manage.py runserver 0.0.0.0:8004

# Terminal 2: other services (cart, payment, etc.)
# cd services/cart_service && python manage.py runserver 0.0.0.0:8003
# cd services/payment_service && python manage.py runserver 0.0.0.0:8005
# etc.

# Terminal 3: test
curl http://localhost:8004/health/
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/
```

---

## 📋 Service Network Map

```
┌─────────────────────────────────────────────────────────┐
│                  TECHSHOP MICROSERVICES                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Gateway (Nginx/Kong)                                  │
│  ├─ Port: 80/443                                       │
│  └─ Routes to all services                             │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ Order Service (orchestra & checkout mgmt)      │   │
│  ├────────────────────────────────────────────────┤   │
│  │ Port: 8004 | DB: postgresql:5437               │   │
│  │                                                │   │
│  │ Calls:                                         │   │
│  │  → Cart Service (8003)                        │   │
│  │  → Inventory Service (8007)                   │   │
│  │  → Payment Service (8005)                     │   │
│  │  → Shipping Service (8008)                    │   │
│  │  → User Service (8000) [optional]             │   │
│  │                                                │   │
│  │ Receives Callbacks:                            │   │
│  │  ← Payment Service (payment-success/failed)   │   │
│  │  ← Shipping Service (shipment events) [future]│   │
│  │                                                │   │
│  └────────────────────────────────────────────────┘   │
│         ↑        ↑        ↑        ↑                   │
│         │        │        │        │                   │
│    ┌────┴───┬────┴───┬────┴───┬────┴───┐              │
│    │        │        │        │        │              │
│    ├─────────────────────────────────────┤            │
│    │ Cart   │Payment │InventoryShipping  │            │
│    │ Service│Service │Service    Service │            │
│    │ :8003  │:8005   │ :8007     :8008   │            │
│    ├─────────────────────────────────────┤            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Service Ports Reference

| Service | Port | DB Port | Status Endpoint |
|---------|------|---------|-----------------|
| Gateway | 80/443 | - | - |
| User Service | 8000 | 5430 | /health/ |
| **Order Service** | **8004** | **5437** | **/health/** |
| Cart Service | 8003 | 5431 | /health/ |
| Payment Service | 8005 | 5432 | /health/ |
| Product Service | 8006 | 5433 | /health/ |
| Inventory Service | 8007 | 5434 | /health/ |
| Shipping Service | 8008 | 5435 | /health/ |
| AI Service | 8009 | 5438 | /health/ |

---

## ✅ Synchronization Checklist

### 1. Order Service Setup ✅

```bash
# ✅ Code exists
ls services/order_service/modules/order/
# Should show: domain/, application/, infrastructure/, presentation/

# ✅ Migrations created
ls services/order_service/modules/order/infrastructure/migrations/
# Should show: 0001_initial.py

# ✅ Settings updated
grep "modules.order" services/order_service/config/settings.py
# Expected: "modules.order" in INSTALLED_APPS

# ✅ URLs integrated
grep "modules.order" services/order_service/config/urls.py
# Expected: include("modules.order.presentation.urls")

# ✅ Requirements satisfied
pip list | grep -E "Django|djangorestframework|httpx|psycopg"
# Expected: Django, djangorestframework, httpx, psycopg2-binary listed
```

### 2. Database Sync ✅

```bash
# ✅ Database created
psql -l | grep order_service
# Expected: order_service | order_service | UTF8

# ✅ Migrations applied
python manage.py showmigrations modules.order
# Expected: [X] modules.order 0001_initial

# ✅ Tables exist
python manage.py dbshell
\dt order_*
# Expected: 3 tables (order_ordermodel, order_orderitemmodel, order_orderstatushistorymodel)

# ✅ Demo data seeded (dev only)
python manage.py seed_orders --count=1
SELECT COUNT(*) FROM order_ordermodel;
# Expected: >= 1
```

### 3. Service URLs Sync ✅

```bash
# ✅ Local services running
for port in 8003 8004 8005 8007 8008; do
  echo "Port $port:"
  curl -s http://localhost:$port/health/ | head -c 50
  echo ""
done

# ✅ .env configured
grep -E "CART_SERVICE_URL|PAYMENT_SERVICE_URL" services/order_service/.env
# Expected: All SERVICE_URLs point to running services
```

### 4. API Endpoints Sync ✅

```bash
# ✅ Health endpoint
curl http://localhost:8004/health/
# Expected: {"status": "ok"}

# ✅ API docs
curl http://localhost:8004/api/docs/ | grep -c "Order"
# Expected: >0 (Swagger docs contain Order endpoints)

# ✅ List orders endpoint
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/ 2>/dev/null | python -m json.tool | head
# Expected: JSON response with "results" or "data" array
```

### 5. Admin Interface Sync ✅

```bash
# ✅ Admin registered
python manage.py shell << EOF
from django.apps import apps
Order = apps.get_model('order', 'OrderModel')
print("Order model registered:", Order)
EOF

# ✅ Superuser exists
python manage.py shell << EOF
from django.contrib.auth.models import User
count = User.objects.filter(is_superuser=True).count()
print(f"Superusers: {count}")
EOF

# ✅ Admin accessible
# Open http://localhost:8004/admin/ and login
```

### 6. Tests Sync ✅

```bash
# ✅ Tests exist
ls services/order_service/modules/order/tests/
# Expected: test_order_service.py

# ✅ Tests pass
python manage.py test modules.order.tests --verbosity=0
# Expected: OK (no errors)

# ✅ Test count
python manage.py test modules.order.tests --collect-only 2>/dev/null | grep -c "test_"
# Expected: >=10 tests
```

### 7. Inter-Service Sync ✅

```bash
# ✅ Cart Service responds
curl http://localhost:8003/health/
# Expected: {"status": "ok"} or similar

# ✅ Payment Service responds
curl http://localhost:8005/health/
# Expected: {"status": "ok"} or similar

# ✅ Inventory Service responds
curl http://localhost:8007/health/
# Expected: {"status": "ok"} or similar

# ✅ Shipping Service responds
curl http://localhost:8008/health/
# Expected: {"status": "ok"} or similar

# ✅ Service key configured
grep "INTERNAL_SERVICE_KEY" services/order_service/.env
# Expected: Non-empty value
```

---

## 🧪 Quick Test Suite

### Basic Connectivity

```bash
# Health check all services
for port in 8000 8003 8004 8005 8006 8007 8008 8009; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health/ | head -c 20
  echo ""
done
```

### Order Service Specific

```bash
# Generate test UUID
TEST_USER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
echo "Test User ID: $TEST_USER_ID"

# Test 1: List orders (no orders yet)
curl -H "X-User-ID: $TEST_USER_ID" \
  -s http://localhost:8004/api/v1/orders/ | python -m json.tool

# Test 2: Try invalid request (missing header)
curl -s http://localhost:8004/api/v1/orders/ | python -m json.tool
# Expected: 401 Unauthorized

# Test 3: Create order (placeholder - requires cart integration)
curl -X POST -H "X-User-ID: $TEST_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_id": "test-cart-123",
    "shipping_address": {
      "receiver_name": "Test User",
      "receiver_phone": "+84912345678",
      "line1": "123 Main St",
      "ward": "Ward 1",
      "district": "District 1",
      "city": "HCMC",
      "country": "Vietnam"
    }
  }' \
  http://localhost:8004/api/v1/orders/from-cart/
```

### Database Verification

```bash
# Connect to order_service database
psql -U order_service -d order_service << EOF
-- Count tables
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'public';

-- Show table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) 
FROM pg_stat_user_tables 
ORDER BY relname;

-- Count orders
SELECT COUNT(*) FROM order_ordermodel;

-- Show latest order
SELECT order_number, status, created_at FROM order_ordermodel 
ORDER BY created_at DESC LIMIT 1;
EOF
```

---

## 🔄 Sync with Git

```bash
# Check status
git status services/order_service/

# Expected: No uncommitted changes

# Check latest commit
git log --oneline services/order_service/ -5

# Pull latest changes
git pull origin main

# Push changes when ready
git add services/order_service/
git commit -m "Updates to order_service"
git push origin main
```

---

## 🐳 Docker Sync

```bash
# Check images
docker images | grep order

# Expected: order_service:latest, order_service:0.1.0, etc.

# Check containers
docker ps | grep order

# Check networks
docker network ls | grep techshop

# Verify network connectivity
docker network inspect techshop

# Check logs
docker logs order_service -n 50
```

---

## 📊 Status Dashboard Script

Save as `status.sh`:

```bash
#!/bin/bash
echo "=== TECHSHOP SERVICES STATUS ==="
echo ""

services=("8000:User" "8003:Cart" "8004:Order" "8005:Payment" "8006:Product" "8007:Inventory" "8008:Shipping")

for svc in "${services[@]}"; do
  port="${svc%%:*}"
  name="${svc##*:}"
  status=$(curl -s http://localhost:$port/health/ 2>&1)
  if echo "$status" | grep -q "ok"; then
    echo "✅ $name (Port $port): RUNNING"
  else
    echo "❌ $name (Port $port): DOWN"
  fi
done

echo ""
echo "=== ORDER SERVICE DETAILS ==="
echo "Database:"
psql -U order_service -d order_service -c "SELECT COUNT(*) as orders FROM order_ordermodel;" 2>/dev/null || echo "  ❌ Database unavailable"

echo ""
echo "API Tests:"
USER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
RESULT=$(curl -s -H "X-User-ID: $USER_ID" http://localhost:8004/api/v1/orders/)
echo "  GET /api/v1/orders/: $(echo $RESULT | python -m json.tool | head -c 50)..."

echo ""
echo "=== END STATUS ==="
```

Run:
```bash
chmod +x status.sh
./status.sh
```

---

## 📚 Documentation Quick Links

| Document | Purpose |
|----------|---------|
| [QUICK_START_ORDER_SERVICE.md](QUICK_START_ORDER_SERVICE.md) | 5-min setup |
| [ORDER_SERVICE_COMPLETION_SUMMARY.md](ORDER_SERVICE_COMPLETION_SUMMARY.md) | What's completed |
| [DEPLOYMENT_AND_INTEGRATION_GUIDE.md](DEPLOYMENT_AND_INTEGRATION_GUIDE.md) | Full deployment |
| [services/order_service/README.md](services/order_service/README.md) | Service overview |
| [services/order_service/modules/order/README.md](services/order_service/modules/order/README.md) | Full architecture (40+ sections) |

---

## 🆘 Quick Troubleshooting

| Problem | Check | Solution |
|---------|-------|----------|
| 401 Unauthorized | X-User-ID header | Add `-H "X-User-ID: $(uuidgen)"` to curl |
| Database connection error | PostgreSQL running | `psql -U postgres -c "SELECT 1"` |
| Service not found | Port mapping | Check docker-compose.yml ports |
| Migrations failed | Migration status | `python manage.py showmigrations modules.order` |
| Admin login failed | Superuser exists | `python manage.py createsuperuser` |
| Inter-service error | Service URLs | Check .env SERVICE_URL variables |
| Tests failing | Test database | `python manage.py test --keepdb` |

---

## 📝 Environment Verification

```bash
# Show environment variables
grep -E "SERVICE|DB_|INTERNAL" services/order_service/.env

# Expected output:
# SERVICE_NAME=order_service
# SERVICE_PORT=8004
# DB_HOST=localhost (or service name in Docker)
# DB_PORT=5437
# CART_SERVICE_URL=http://localhost:8003
# PAYMENT_SERVICE_URL=http://localhost:8005
# INTERNAL_SERVICE_KEY=<set>
# etc.
```

---

## 🎯 Sync Validation Command

Run all checks at once:

```bash
#!/bin/bash
check() {
  if eval "$1" > /dev/null 2>&1; then
    echo "✅ $2"
    return 0
  else
    echo "❌ $2"
    return 1
  fi
}

echo "Checking Order Service Sync..."
check "cd services/order_service" "Directory exists"
check "grep 'modules.order' config/settings.py" "App registered"
check "ls modules/order/infrastructure/migrations/0001_initial.py" "Migration exists"
check "curl -s http://localhost:8004/health/" "Service running"
check "psql -lqt | grep -q order_service" "Database exists"
check "curl -s -H 'X-User-ID: test' http://localhost:8004/api/v1/orders/" "API accessible"

echo "Sync check complete!"
```

---

## ✨ Pro Tips

- Use `docker-compose ps` to see all service status at once
- Set up your shell profile to alias service commands:
  ```bash
  alias os='cd services/order_service'
  alias ostart='cd services/order_service && python manage.py runserver 0.0.0.0:8004'
  alias otest='cd services/order_service && python manage.py test modules.order.tests'
  ```
- Keep one terminal per service while developing
- Use `tail -f` on service logs to see real-time activity
- Use Postman collection to test all API endpoints

---

**Status**: ✅ Everything Synced & Ready

**Last Check**: $(date)

---

For detailed info, see [ORDER_SERVICE_COMPLETION_SUMMARY.md](ORDER_SERVICE_COMPLETION_SUMMARY.md)
