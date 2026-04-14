# Deployment & Integration Guide - Order Service

**Complete guide to deploy order_service and integrate with other services.**

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Inter-Service Integration](#inter-service-integration)
5. [Database Setup](#database-setup)
6. [Testing & Verification](#testing--verification)
7. [Production Deployment](#production-deployment)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Procedures](#rollback-procedures)

---

## ✅ Pre-Deployment Checklist

Before starting deployment, verify:

```bash
# 1. Check Python version
python --version
# Expected: Python 3.9+

# 2. Check PostgreSQL installed
psql --version
# Expected: PostgreSQL 12+

# 3. Check Git (for version control)
git --version

# 4. Check Docker (for containerization)
docker --version
docker-compose --version

# 5. Check virtual environment
python -m venv --help

# 6. Verify workspace
ls -la services/order_service/
# Should show: manage.py, config/, modules/, etc.
```

**Environment Readiness**:
- ✅ Python 3.9+ installed
- ✅ PostgreSQL running (or Docker ready)
- ✅ Virtual environment created
- ✅ Git repository initialized

---

## 🚀 Local Development Setup

### Step 1: Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Verify activation (should show cursor with (venv) prefix)
```

### Step 2: Install Dependencies

```bash
cd services/order_service

pip install --upgrade pip setuptools wheel

pip install -r requirements.txt

# Verify installations
pip list | grep -E "Django|djangorestframework|httpx|psycopg"
```

### Step 3: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
cat > .env << EOF
# Service Config
SERVICE_NAME=order_service
SERVICE_PORT=8004
DEBUG=True

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=order_service
DB_USER=order_service
DB_PASSWORD=order_service_password
DB_HOST=localhost
DB_PORT=5432

# Inter-service URLs
CART_SERVICE_URL=http://localhost:8003
INVENTORY_SERVICE_URL=http://localhost:8007
PAYMENT_SERVICE_URL=http://localhost:8005
SHIPPING_SERVICE_URL=http://localhost:8008

# Security
INTERNAL_SERVICE_KEY=dev-service-key
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Settings
TIME_ZONE=UTC
LOG_LEVEL=INFO
UPSTREAM_TIMEOUT=5
CORS_ALLOW_ALL_ORIGINS=true
EOF
```

### Step 4: Database Setup

```bash
# Option A: PostgreSQL (Recommended)
createuser order_service -P
# Enter password: order_service_password

createdb -O order_service order_service

# Verify connection
psql -U order_service -d order_service -c "SELECT 1"
# Should return: (1 row)

# Option B: SQLite (Quick Dev)
# No setup needed, Django creates automatically
# (Edit settings.py to use SQLite)
```

### Step 5: Django Migrations

```bash
# Show migration status
python manage.py showmigrations modules.order

# Run migrations
python manage.py migrate

# Verify tables created
python manage.py dbshell
\dt order_*
# Should show: order_ordermodel, order_orderitemmodel, order_orderstatushistorymodel
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts
# Username: admin
# Email: admin@example.com
# Password: (enter secure password)
```

### Step 7: Seed Demo Data

```bash
# Create 10 demo orders
python manage.py seed_orders --count=10

# Verify
python manage.py dbshell
SELECT COUNT(*) FROM order_ordermodel;
# Should return: 10
```

### Step 8: Start Development Server

```bash
python manage.py runserver 0.0.0.0:8004

# Output should show:
# Starting development server at http://0.0.0.0:8004/
# Quit the server with CONTROL-C
```

### Verification

```bash
# In another terminal:

# Health check
curl http://localhost:8004/health/

# API docs
curl http://localhost:8004/api/docs/

# Admin panel
# Open http://localhost:8004/admin/ in browser
# Login with superuser credentials
```

---

## 🐳 Docker Deployment

### Step 1: Build Docker Image

```bash
# From order_service directory
cd services/order_service

# Build image
docker build -t order_service:latest .

# Tag version
docker tag order_service:latest order_service:1.0.0

# Verify image
docker images | grep order_service
```

### Step 2: Run Container (Standalone)

```bash
# Create network (for inter-service communication)
docker network create techshop

# Run container
docker run -d \
  --name order_service \
  --network techshop \
  -p 8004:8004 \
  --env-file .env \
  -e DB_HOST=order_service_db \
  order_service:latest

# Check container status
docker ps | grep order_service
docker logs order_service
```

### Step 3: Docker Compose (Full Stack)

```bash
# From monorepo root
cd /path/to/TechShop

# Create docker-compose.yml (if not exists)
cat > docker-compose-order.yml << EOF
version: '3.9'

services:
  order_service_db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: order_service
      POSTGRES_PASSWORD: order_service_password
      POSTGRES_DB: order_service
    ports:
      - "5437:5432"
    volumes:
      - order_service_db_data:/var/lib/postgresql/data

  order_service:
    build:
      context: ./services/order_service
      dockerfile: Dockerfile
    environment:
      DB_HOST: order_service_db
      DB_PORT: 5432
      DB_NAME: order_service
      DB_USER: order_service
      DB_PASSWORD: order_service_password
      SERVICE_PORT: 8004
      DEBUG: "false"
      INTERNAL_SERVICE_KEY: dev-service-key
    ports:
      - "8004:8004"
    depends_on:
      - order_service_db
    networks:
      - techshop

networks:
  techshop:
    external: true

volumes:
  order_service_db_data:
EOF

# Start services
docker-compose -f docker-compose-order.yml up -d

# Verify
docker-compose -f docker-compose-order.yml logs -f order_service
```

### Step 4: Container Management

```bash
# View logs
docker logs order_service -f

# Execute command in container
docker exec order_service python manage.py seed_orders --count=5

# Stop container
docker stop order_service

# Restart container
docker restart order_service

# Remove container
docker rm order_service
```

---

## 🔗 Inter-Service Integration

### Step 1: Service Discovery

Verify all dependent services are running:

```bash
# Cart Service
curl http://localhost:8003/health/

# Inventory Service
curl http://localhost:8007/health/

# Payment Service
curl http://localhost:8005/health/

# Shipping Service
curl http://localhost:8008/health/

# All should return: {"status": "ok"}
```

### Step 2: Update Service URLs

Edit `.env` in order_service with actual service URLs:

```bash
# Local Development
CART_SERVICE_URL=http://localhost:8003
INVENTORY_SERVICE_URL=http://localhost:8007
PAYMENT_SERVICE_URL=http://localhost:8005
SHIPPING_SERVICE_URL=http://localhost:8008

# Docker Development
CART_SERVICE_URL=http://cart_service:8003
INVENTORY_SERVICE_URL=http://inventory_service:8007
PAYMENT_SERVICE_URL=http://payment_service:8005
SHIPPING_SERVICE_URL=http://shipping_service:8008

# Production (Example)
CART_SERVICE_URL=https://cart.techshop.io
INVENTORY_SERVICE_URL=https://inventory.techshop.io
PAYMENT_SERVICE_URL=https://payment.techshop.io
SHIPPING_SERVICE_URL=https://shipping.techshop.io
```

### Step 3: Service-to-Service Auth

Set internal service key (used in X-Internal-Service-Key header):

```bash
# Generate secure key
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
# Output: abc123def456ghi789jkl...

# Add to order_service .env
INTERNAL_SERVICE_KEY=abc123def456ghi789jkl...

# Share key with other services (must match in all services)
# Each service validates this header on internal endpoints
```

### Step 4: Test Inter-Service Communication

```bash
# Test Cart Service connection
python manage.py shell
>>> from modules.order.infrastructure.clients import CartServiceClient
>>> client = CartServiceClient()
>>> client.validate_cart("test-cart-id")  # Should succeed or raise connection error

# Test Inventory Service connection
>>> from modules.order.infrastructure.clients import InventoryServiceClient
>>> client = InventoryServiceClient()
>>> # Test methods available

# Similar for Payment & Shipping
```

### Step 5: Configure Service Callbacks

Order Service receives callbacks from Payment Service. Configure Payment Service to send callbacks:

```json
// Payment Service Config
{
  "order_service_url": "http://localhost:8004",
  "order_service_key": "dev-service-key",
  "payment_success_endpoint": "/api/v1/internal/orders/{order_id}/payment-success/",
  "payment_failed_endpoint": "/api/v1/internal/orders/{order_id}/payment-failed/"
}
```

---

## 🗄️ Database Setup (Detailed)

### PostgreSQL Setup

```bash
# Connect as superuser
psql -U postgres

# Create user
CREATE USER order_service WITH PASSWORD 'order_service_password';

# Create database
CREATE DATABASE order_service OWNER order_service;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE order_service TO order_service;

# Connect as order_service user
\c order_service order_service

# Create extensions (if needed)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Verify
SELECT current_user;
\dt  # Should be empty initially
```

### Initial Migration

```bash
# Show migrations
python manage.py showmigrations modules.order
# Output:
# modules.order
#  [ ] 0001_initial

# Run migration
python manage.py migrate modules.order
# Output:
# Applying modules.order.0001_initial... OK

# Verify tables
python manage.py dbshell
\dt order_*
# Output:
# List of relations
# Schema |              Name              | Type  | Owner
# --------+--------------------------------+-------+--
# public | order_orderitemmodel           | table | order_service
# public | order_ordermodel               | table | order_service
# public | order_orderstatushistorymodel  | table | order_service

# Check table structure
\d order_ordermodel
# Should show all fields, indexes, constraints
```

### Backup & Restore

```bash
# Backup database
pg_dump -U order_service order_service > order_service_backup.sql

# Restore database
psql -U order_service order_service < order_service_backup.sql

# Backup specific table
pg_dump -U order_service -t order_ordermodel order_service > orders_backup.sql
```

---

## 🧪 Testing & Verification

### Unit Tests

```bash
# Run all tests
python manage.py test modules.order.tests -v 2

# Run specific test class
python manage.py test modules.order.tests.test_order_service.OrderEntityTests -v 2

# Run with coverage
coverage run --source='modules.order' manage.py test modules.order.tests
coverage report
coverage html  # Generate HTML report
```

### Integration Tests

```bash
# Create test fixture with sample cart data
python manage.py shell << EOF
from modules.order.domain.value_objects import Money, OrderNumber
from modules.order.infrastructure.models import OrderModel

# Create test order
OrderModel.objects.create(
    order_number="ORD-20240101-000001",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    status="pending",
    payment_status="unpaid",
    fulfillment_status="unfulfilled",
    grand_total=100000,
    currency="VND"
)
print("Test order created")
EOF

# Test API endpoint
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/
```

### API Testing with Postman

```json
// Create order from cart
POST /api/v1/orders/from-cart/
Headers: {
  "X-User-ID": "550e8400-e29b-41d4-a716-446655440000",
  "Content-Type": "application/json"
}
Body: {
  "cart_id": "test-cart-123",
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
}

// Expected Response (201 Created)
{
  "success": true,
  "message": "Order created successfully",
  "data": {
    "id": "...",
    "order_number": "ORD-20240101-000001",
    "status": "awaiting_payment",
    "payment_status": "pending",
    "items": [...],
    "totals": {...}
  }
}
```

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class OrderUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_orders(self):
        headers = {"X-User-ID": "550e8400-e29b-41d4-a716-446655440000"}
        self.client.get("/api/v1/orders/", headers=headers)
    
    @task
    def get_order_detail(self):
        headers = {"X-User-ID": "550e8400-e29b-41d4-a716-446655440000"}
        self.client.get("/api/v1/orders/1/", headers=headers)
EOF

# Run load test
locust -f locustfile.py --host=http://localhost:8004
# Open http://localhost:8089 in browser
```

---

## 🌍 Production Deployment

### Step 1: Pre-Production Checklist

```bash
# Update .env for production
cat > .env.prod << EOF
DEBUG=False
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=order.techshop.io,www.order.techshop.io
DB_HOST=prod-db.techshop.io
DB_USER=order_service
DB_PASSWORD=$(openssl rand -base64 32)
INTERNAL_SERVICE_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
EOF

# Run security checks
python manage.py check --deploy
```

### Step 2: Kubernetes Deployment (Example)

```yaml
# k8s-order-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: techshop
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
      - name: order-service
        image: order_service:latest
        ports:
        - containerPort: 8004
        env:
        - name: DB_HOST
          value: "postgres.techshop.svc.cluster.local"
        - name: DEBUG
          value: "false"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready/
            port: 8004
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: techshop
spec:
  selector:
    app: order-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8004
  type: ClusterIP
```

Deploy:
```bash
kubectl apply -f k8s-order-service.yaml
kubectl rollout status deployment/order-service -n techshop
```

### Step 3: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/order.techshop.io
upstream order_service {
    server order_service_1:8004;
    server order_service_2:8004;
    server order_service_3:8004;
}

server {
    listen 80;
    server_name order.techshop.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name order.techshop.io;
    
    ssl_certificate /etc/letsencrypt/live/order.techshop.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/order.techshop.io/privkey.pem;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://order_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
    
    location /static/ {
        alias /app/staticfiles/;
    }
}
```

---

## 📊 Monitoring & Logs

### Application Logs

```bash
# View logs
docker logs order_service -f

# View logs with timestamps
docker logs order_service --timestamps -f

# View last N lines
docker logs order_service --tail=100

# Tail logs from multiple containers
docker logs order_service -f 2>&1 | tee order_service.log
```

### Metrics Monitoring

```bash
# Install monitoring stack
pip install prometheus-client

# Metrics endpoint
curl http://localhost:8004/metrics/
```

### Database Monitoring

```bash
# Connect to database
psql -U order_service -d order_service

# Show database size
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'order_service';

# Show table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

# Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## 🔧 Troubleshooting

### Database Connection Error

```
Error: could not translate host name "orders_service_db" to address
```

**Solution**:
```bash
# Check Docker network
docker network inspect techshop

# Verify service name in docker-compose.yml
# Ensure DB_HOST matches service name
docker-compose ps
```

### Migration Errors

```
Error: relation "order_ordermodel" already exists
```

**Solution**:
```bash
# Check migration status
python manage.py showmigrations modules.order

# Rollback to previous state
python manage.py migrate modules.order 0000

# Re-run migrations
python manage.py migrate modules.order
```

### Permission Denied on API

```
Error: 401 Unauthorized - Missing X-User-ID header
```

**Solution**:
```bash
# Always include X-User-ID header
curl -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  http://localhost:8004/api/v1/orders/
```

### Inter-Service Connection Failure

```
Error: Connection refused - Cart Service unavailable
```

**Solution**:
```bash
# Check service URLs in .env
cat .env | grep SERVICE_URL

# Verify services are running
curl http://localhost:8003/health/
curl http://localhost:8007/health/
curl http://localhost:8005/health/
curl http://localhost:8008/health/

# Check firewall rules
sudo ufw allow 8003:8008/tcp
```

---

## ↩️ Rollback Procedures

### Database Rollback

```bash
# List migrations
python manage.py showmigrations modules.order

# Rollback to specific migration
python manage.py migrate modules.order 0001_initial

# Rollback all migrations (remove all tables)
python manage.py migrate modules.order zero

# Verify rollback
python manage.py showmigrations modules.order
```

### Code Rollback

```bash
# Using Git
git log --oneline services/order_service/

# Checkout previous version
git checkout HEAD~1 services/order_service/

# Or rollback specific file
git checkout <commit-hash> services/order_service/modules/order/presentation/api.py

# Or using branches
git checkout production services/order_service/
git merge develop  # Back to previous state
```

### Docker Rollback

```bash
# Stop current container
docker stop order_service

# Remove current container
docker rm order_service

# Use previous image
docker run -d \
  --name order_service \
  -p 8004:8004 \
  --env-file .env \
  order_service:0.9.0  # Previous version tag

# Verify
docker ps | grep order_service
curl http://localhost:8004/health/
```

---

## 📋 Deployment Checklist

- ✅ All dependencies installed
- ✅ Environment variables configured
- ✅ Database created and migrated
- ✅ Demo data seeded (for non-prod)
- ✅ Admin user created
- ✅ All dependent services running
- ✅ Inter-service URLs configured
- ✅ Internal service key shared
- ✅ Tests passing
- ✅ Health endpoints responding
- ✅ API documentation accessible
- ✅ Logs configured
- ✅ Monitoring enabled (production)
- ✅ Backup procedures documented
- ✅ Rollback procedures tested

---

## 📞 Support

For issues, check:
1. [Troubleshooting Section](#troubleshooting)
2. [QUICK_START_ORDER_SERVICE.md](QUICK_START_ORDER_SERVICE.md)
3. [modules/order/README.md](services/order_service/modules/order/README.md)
4. Service logs: `docker logs order_service -f`
5. Database: `psql -U order_service -d order_service`

---

**Deployment Status**: Ready for Development, Testing, and Production

**Last Updated**: December 2024
