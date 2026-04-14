# TechShop Master Seeding Guide

Complete guide for seeding and managing demo data across all TechShop microservices.

## Overview

The master seed script (`shared/scripts/seed_complete_system.py`) populates the entire TechShop system with comprehensive demo data in a single operation.

### What Gets Seeded

1. **Users (4)**: 1 admin, 1 staff, 2 customers
2. **Categories (12+)**: Laptops, Desktops, Phones, Tablets, Monitors, etc.
3. **Brands (10)**: Samsung, Apple, Nokia, Xiaomi, Asus, Dell, Sony, LG, Acer, HP
4. **Products (30-50)**: Across all brands with varied prices and stock levels
5. **Stock/Inventory**: Realistic quantities, some low-stock, some out-of-stock
6. **Carts (2)**: Active carts for demo customers
7. **Orders (5)**: In different states (PENDING, AWAITING_PAYMENT, PAID, SHIPPED, DELIVERED)
8. **Payments (3-4)**: Linked to PAID orders
9. **Shipments (2-3)**: For SHIPPED/DELIVERED orders
10. **AI Knowledge Base (6)**: Shipping, returns, payment, warranty info
11. **AI Events (30+)**: User behavior events for recommendations

### Demo Scenario

**John (john@example.com)**: Strong Samsung preference
- 5 product searches for "Samsung under 10 triệu"
- 10 clicks on Samsung products
- 3 additions to cart
- 1 order (PAID + SHIPPED status)
- **AI recommendation outcome**: Samsung will rank first in recommendations

**Jane (jane@example.com)**: Diverse browser
- Views various products across brands
- Makes purchases from different categories
- **AI outcome**: Diverse recommendations

## Quick Start

### Prerequisites

```bash
# Ensure docker-compose is running
docker-compose up -d

# Verify all services are healthy
curl http://localhost:8005/health  # payment_service
curl http://localhost:8001/health  # user_service
# ... check other services
```

### Run Full Seed

```bash
# From workspace root
python shared/scripts/seed_complete_system.py

# With verbose output
python shared/scripts/seed_complete_system.py --verbose

# Dry-run (shows what would be seeded)
python shared/scripts/seed_complete_system.py --dry-run

# Only specific modules
python shared/scripts/seed_complete_system.py --users-only
python shared/scripts/seed_complete_system.py --products-only
python shared/scripts/seed_complete_system.py --orders-only
```

### Environment Configuration

Set service URLs using environment variables:

```bash
# Linux/Mac
export USER_SERVICE_URL=http://localhost:8001
export PRODUCT_SERVICE_URL=http://localhost:8002
export CART_SERVICE_URL=http://localhost:8003
export ORDER_SERVICE_URL=http://localhost:8004
export PAYMENT_SERVICE_URL=http://localhost:8005
export INVENTORY_SERVICE_URL=http://localhost:8007
export AI_SERVICE_URL=http://localhost:8000
export SHIPPING_SERVICE_URL=http://localhost:8008
export INTERNAL_SERVICE_KEY=internal-secret-key

# Then run
python shared/scripts/seed_complete_system.py --verbose

# Windows PowerShell
$env:USER_SERVICE_URL="http://localhost:8001"
# ... set other URLs
python shared/scripts/seed_complete_system.py --verbose
```

## Seeding Order (Dependency Chain)

The script seeds in this strict order:

```
Users
  ├── Categories
  ├── Brands
  └── Products
      └── Inventory
          ├── Carts
          └── Orders → Payments → Shipments
              └── AI Knowledge Base
                  └── AI Events
```

### Why This Order?

- **Users first**: All other resources belong to users
- **Categories/Brands before Products**: Products reference these
- **Products before Inventory**: Need product IDs to stock them
- **Inventory before Carts/Orders**: Need stock to reserve items
- **Orders before Payments**: Some orders reference payments
- **All data before AI Events**: Events reference products/users

## Verification Commands

### Check Users

```bash
# List all users
curl -s http://localhost:8001/api/v1/internal/users/ \
  -H "X-Internal-Service-Key: internal-secret-key" | jq

# Get specific user
curl -s http://localhost:8001/api/v1/internal/users/by-email/john@example.com/ \
  -H "X-Internal-Service-Key: internal-secret-key" | jq
```

### Check Products

```bash
# List all products
curl -s http://localhost:8002/api/v1/internal/products/?limit=100 \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data.results[] | {id, name, price, brand_id}'

# Count products
curl -s http://localhost:8002/api/v1/internal/products/?limit=1 \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data.pagination.total'
```

### Check Inventory

```bash
# List inventory for product
PRODUCT_ID="<uuid-from-products-list>"
curl -s http://localhost:8007/api/v1/internal/inventory/by-product/$PRODUCT_ID/ \
  -H "X-Internal-Service-Key: internal-secret-key" | jq
```

### Check Orders

```bash
# Get John's orders
USER_ID="<john-user-id>"
curl -s http://localhost:8004/api/v1/internal/orders/by-user/$USER_ID/ \
  -H "X-Internal-Service-Key: internal-secret-key" \
  -H "X-User-ID: $USER_ID" | jq

# Get order detail
ORDER_ID="<order-uuid>"
curl -s http://localhost:8004/api/v1/orders/$ORDER_ID/ \
  -H "X-User-ID: $USER_ID" | jq
```

### Check AI Events

```bash
# Get events for John
curl -s http://localhost:8000/api/v1/internal/ai/events/?user_id=<john-user-id> \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data | length'
```

## Expected Output

```
================================================================================
STARTING COMPLETE SYSTEM SEED
Dry Run: False | Verbose: False
================================================================================

[PHASE 1] Seeding Users...
  ✓ User admin@example.com (admin): 550e8400-e29b-41d4-a716-446655440000
  ✓ User staff@example.com (staff): 550e8400-e29b-41d4-a716-446655440001
  ✓ User john@example.com (customer): 550e8400-e29b-41d4-a716-446655440002
  ✓ User jane@example.com (customer): 550e8400-e29b-41d4-a716-446655440003

[PHASE 2-5] Seeding Product Catalog...
  Seeding Categories...
    ✓ Category: Laptops
    ✓ Category: Desktops
    ... (10+ more)
  Seeding Brands...
    ✓ Brand: Samsung
    ✓ Brand: Apple
    ... (8 more)
  Seeding Products...
    ✓ Product: Galaxy Book Go (Samsung)
    ✓ Product: MacBook Air M1 (Apple)
    ... (30+ more)

[PHASE 6] Seeding Inventory Adjustments...
  ✓ Set OUT OF STOCK: Galaxy Tab S7
  ✓ Set LOW STOCK (3 units): Galaxy Tab S8

[PHASE 7] Seeding Carts...
  ✓ Cart 1 (John): Galaxy Book Go
  ✓ Cart 2 (Jane): Multiple items

[PHASE 8-10] Seeding Orders, Payments, and Shipments...
  ✓ Order ORD-20260411-000001: PENDING
  ✓ Order ORD-20260411-000002: AWAITING_PAYMENT
  ✓ Order ORD-20260411-000003: PAID
    ✓ Payment created
  ... (2 more)

[PHASE 11] Seeding AI Knowledge Base...
  ✓ AI Doc: Shipping Policy
  ✓ AI Doc: Return Policy
  ... (4 more)

[PHASE 12] Seeding AI Behavioral Events...
  ✓ Customer 1 (John): 25 Samsung preference events
  ✓ Customer 2 (Jane): 8 diverse browsing events

================================================================================
SEEDING SUMMARY
================================================================================
USERS: 4 created
CATEGORIES: 12 created
BRANDS: 10 created
PRODUCTS: 45 created
INVENTORY: 45 created
CARTS: 2 created
ORDERS: 5 created
PAYMENTS: 3 created
SHIPMENTS: 0 created
AI_DOCS: 6 created
AI_EVENTS: 33 created
================================================================================
✓ SEEDING COMPLETE!
```

## Troubleshooting

### Services Not Running

```bash
# Check if services are up
docker-compose ps

# View logs for specific service
docker-compose logs -f payment_service
docker-compose logs -f user_service
```

### Address/Host Not Found

Update `SERVICE_URLS` or environment variables in the script:

```python
SERVICE_URLS = {
    "user": "http://user_service:8001",  # For docker-compose network
    # or
    "user": "http://localhost:8001",     # For local testing
}
```

### INTERNAL_SERVICE_KEY Mismatch

Ensure all services use the same internal key:

```bash
# Check .env or docker-compose.yml
grep INTERNAL_SERVICE_KEY docker-compose.yml

# Or set it
export INTERNAL_SERVICE_KEY="internal-secret-key"
```

### Partial Failures

The script is designed to be idempotent. If some resources fail to create, re-run it:

```bash
python shared/scripts/seed_complete_system.py  # Will skip existing resources
```

## Advanced: Seeding in Production

For production environments, consider:

1. **Use separate database backups** (don't mix with real data)
2. **Run specific phases only** (--users-only, --products-only)
3. **Verify before committing**:
   ```bash
   python shared/scripts/seed_complete_system.py --dry-run
   ```
4. **Check data sanity**:
   - All products have inventory
   - All users have valid emails
   - Orders reference existing products/users
5. **Cleanup with custom script** (delete by criteria)

## Demo Scenario Walkthrough

### 1. John's Product Search & Purchase Journey

```bash
# 1. John searches for Samsung
# → Script creates 5 search events in AI service
# → AI service processes events and learns preference

# 2. View John's events
curl -s "http://localhost:8000/api/v1/internal/ai/events/?user_id=<john_id>&event_type=product_search" \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data | length'
# Expected: 5

# 3. View John's cart
curl -s "http://localhost:8003/api/v1/internal/carts/by-user/<john_id>" \
  -H "X-Internal-Service-Key: internal-secret-key" \
  -H "X-User-ID: <john_id>" | jq

# 4. Get John's order
curl -s "http://localhost:8004/api/v1/orders/<order_id>" \
  -H "X-User-ID: <john_id>" | jq '.data.status'
# Expected: "PAID" or "SHIPPED"

# 5. Get AI recommendations for John
curl -s "http://localhost:8000/api/v1/recommendations?user_id=<john_id>" \
  -H "X-User-ID: <john_id>" | jq '.data[0].brand_name'
# Expected: "Samsung" (first in list)
```

### 2. Jane's Diverse Browsing

```bash
# 1. View Jane's browsing events (should be diverse across brands)
curl -s "http://localhost:8000/api/v1/internal/ai/events/?user_id=<jane_id>" \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data[].product_id' | sort -u | wc -l
# Expected: 8+ different products

# 2. Get Jane's cart
curl -s "http://localhost:8003/api/v1/internal/carts/by-user/<jane_id>" \
  -H "X-Internal-Service-Key: internal-secret-key" | jq

# 3. Get Jane's orders
curl -s "http://localhost:8004/api/v1/orders?user_id=<jane_id>" \
  -H "X-User-ID: <jane_id>" | jq '.data | length'
```

## Cleanup

To remove seeded data:

```bash
# Option 1: Delete by user email
DELETE /api/v1/internal/users/by-email/john@example.com/
DELETE /api/v1/internal/users/by-email/jane@example.com/
DELETE /api/v1/internal/users/by-email/admin@example.com/
DELETE /api/v1/internal/users/by-email/staff@example.com/

# Option 2: Full database reset (danger!)
docker-compose down -v  # Remove all volumes
docker-compose up -d    # Restart with fresh databases
```

## Summary Checklist

After running the seed script, verify:

- [x] 4 users created (admin, staff, john, jane)
- [x] 10+ categories exist
- [x] 10 brands exist
- [x] 30-50 products exist with prices
- [x] All products have inventory > 0
- [x] 2-3 products out of stock
- [x] 2-3 products low stock
- [x] 2 active carts exist
- [x] 5 orders in different states
- [x] 3-4 payments exist
- [x] 6+ AI knowledge documents
- [x] 30+ AI behavioral events
- [x] John's orders all use Samsung
- [x] Jane's orders use diverse brands

---

**Last Updated**: April 11, 2026
**Status**: Production Ready
**Tested With**: Docker Compose, Local Environment
