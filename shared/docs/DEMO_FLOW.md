# TechShop E2E Demo Runbook

**Version:** 1.0  
**Date:** April 11, 2026  
**Purpose:** Complete walkthrough of TechShop microservices functioning end-to-end

## QUICK START (5 minutes)

```bash
# 1. Start everything
docker-compose up --build -d

# 2. Wait for services to be ready (check logs)
docker-compose logs -f user_service | grep "Running on"

# 3. Seed demo data
python shared/scripts/seed_complete_system.py --verbose

# 4. Run E2E tests
python shared/scripts/e2e_integration_test.py --verbose

# Expected: All tests pass ✅
```

## DEMO ACCOUNTS & CREDENTIALS

### Test Users (Pre-seeded)

```
ADMIN:
- Email: admin@techshop.local
- Password: AdminPass123!
- Role: ADMIN
- Use for: Admin dashboard, inventory management

STAFF:
- Email: staff@techshop.local
- Password: StaffPass123!
- Role: STAFF
- Use for: Product management, order monitoring

CUSTOMER 1 (Demo Shopper):
- Email: john.doe@techshop.local
- Password: CustomerPass123!
- Role: CUSTOMER
- Preference: Samsung electronics under 10M VND
- Use for: Normal shopping flow

CUSTOMER 2 (Diverse Shopper):
- Email: jane.smith@techshop.local
- Password: CustomerPass123!
- Role: CUSTOMER
- Preference: Mixed interests
- Use for: Testing diverse recommendations
```

## API ACCESS

### Service URLs

| Service | URL | Docs |
|---------|-----|------|
| Gateway / Frontend | http://localhost:80/ | N/A |
| User Service | http://localhost:8001/ | /api/docs/ |
| Product Service | http://localhost:8002/ | /api/docs/ |
| Cart Service | http://localhost:8003/ | /api/docs/ |
| Order Service | http://localhost:8004/ | /api/docs/ |
| Payment Service | http://localhost:8005/ | /api/docs/ |
| Product Service DB | localhost:5442 | (PostgreSQL) |
| Inventory Service | http://localhost:8007/ | /api/docs/ |
| Shipping Service | http://localhost:8008/ | /api/docs/ |
| AI Service | http://localhost:8000/ | /api/docs/ |

### Base URLs for Examples

```bash
# User Service examples
curl http://localhost:8001/api/v1/auth/login/

# Product Service examples
curl http://localhost:8002/api/v1/catalog/products/

# Admin Access
curl -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8007/api/v1/admin/inventory/stock-items/
```

---

## DEMO FLOW #1: Browse Catalog & AI Recommendations (10 min)

**Scenario:** Customer wants to find a Samsung laptop under 10M VND

### Step 1.1: Login as Customer

```bash
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@techshop.local",
    "password": "CustomerPass123!"
  }'

# Response:
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access": "<JWT_TOKEN>",
    "refresh": "<REFRESH_TOKEN>",
    "user": {
      "id": "user-uuid",
      "email": "john.doe@techshop.local",
      "full_name": "John Doe",
      "role": "customer"
    }
  }
}

# Save the token for subsequent requests
export TOKEN="<JWT_TOKEN_from_response>"
```

### Step 1.2: List Products / Search

```bash
# List all products
curl http://localhost:8002/api/v1/catalog/products/

# Search for Samsung
curl "http://localhost:8002/api/v1/catalog/products/?brand=Samsung&category=Smartphone"

# Response example:
{
  "success": true,
  "data": {
    "count": 12,
    "results": [
      {
        "id": "prod-uuid-1",
        "name": "Samsung Galaxy S24",
        "brand": "Samsung",
        "category": "Smartphone",
        "base_price": 8990000,
        "currency": "VND",
        "status": "active",
        "thumbnail_url": "https://..."
      },
      ...
    ]
  }
}
```

### Step 1.3: Get Personalized Recommendations

```bash
# Get AI recommendations for this user
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/ai/recommendations/

# Response: Top recommended products based on browsing history
{
  "success": true,
  "data": {
    "total_count": 5,
    "products": [
      {
        "id": "prod-uuid-1",
        "name": "Samsung Galaxy S24",
        "brand": "Samsung",
        "score": 85,
        "reason_codes": ["preferred_brand", "preferred_price_range"]
      },
      ...
    ]
  }
}
```

### Step 1.4: Ask AI Chat for Recommendations

```bash
# Create a chat session
SESSION=$(curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/ai/chat/sessions/ \
  -d '{"session_title": "Shopping Help"}' | jq -r '.data.id')

# Ask a question
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/ai/chat/ask/ \
  -d "{
    \"session_id\": \"$SESSION\",
    \"message\": \"Điện thoại Samsung nào dưới 10 triệu?\",
    \"user_id\": \"$(curl -H 'Authorization: Bearer $TOKEN' http://localhost:8001/api/v1/auth/me/ | jq -r '.data.id')\"
  }"

# Response: AI retrieves recommendations using profile + knowledge base
{
  "success": true,
  "data": {
    "message_id": "msg-uuid",
    "chat_response": "Dựa vào lịch sử tìm kiếm của bạn...",
    "recommended_products": [
      {"name": "Samsung Galaxy S24", "price": 8990000},
      ...
    ],
    "sources": [
      "product_catalog",
      "user_preferences"
    ]
  }
}
```

---

## DEMO FLOW #2: Complete Purchase (15 min)

**Scenario:** Customer adds Samsung to cart and completes purchase

### Step 2.1: Add Product to Cart

```bash
# Get a Samsung product ID from earlier search
PRODUCT_ID="prod-uuid-from-search"

curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8003/api/v1/cart/items/ \
  -d "{
    \"product_id\": \"$PRODUCT_ID\",
    \"quantity\": 1
  }"

# Response: Updated cart
{
  "success": true,
  "data": {
    "id": "cart-uuid",
    "user_id": "user-uuid",
    "items": [
      {
        "id": "item-uuid",
        "product_id": "$PRODUCT_ID",
        "quantity": 1,
        "unit_price": 8990000,
        "line_total": 8990000,
        "product_name": "Samsung Galaxy S24"
      }
    ],
    "subtotal_amount": 8990000,
    "item_count": 1
  }
}
```

### Step 2.2: Get Checkout Preview

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8003/api/v1/cart/checkout-preview/

# Response: About to place order
{
  "success": true,
  "data": {
    "is_valid": true,
    "cart": {
      "id": "cart-uuid",
      "subtotal_amount": 8990000,
      "item_count": 1
    },
    "issues": [],
    "checkout_payload": {
      "subtotal_amount": 8990000,
      "items": [...]
    }
  }
}
```

### Step 2.3: Get User Address (for shipping)

```bash
# Get user profile and addresses
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/v1/profile/addresses/

# Response: User's saved addresses
{
  "success": true,
  "data": [
    {
      "id": "address-uuid",
      "receiver_name": "John Doe",
      "receiver_phone": "+84123456789",
      "line1": "123 Nguyen Hue",
      "district": "District 1",
      "city": "Ho Chi Minh",
      "country": "Vietnam",
      "is_default": true
    }
  ]
}
```

### Step 2.4: Create Order

```bash
CART_ID="cart-uuid-from-step-2.1"

curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8004/api/v1/orders/ \
  -d "{
    \"cart_id\": \"$CART_ID\",
    \"shipping_address\": {
      \"receiver_name\": \"John Doe\",
      \"receiver_phone\": \"+84123456789\",
      \"line1\": \"123 Nguyen Hue\",
      \"district\": \"District 1\",
      \"city\": \"Ho Chi Minh\",
      \"country\": \"Vietnam\"
    }
  }"

# Response: Order created, waiting for payment
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "order_number": "ORD-20260411-123456",
    "status": "awaiting_payment",
    "payment_status": "pending",
    "grand_total_amount": 8990000,
    "currency": "VND",
    "payment_id": "payment-uuid",
    "payment_checkout_url": "https://payment-provider.com/checkout?id=...",
    "items": [...]
  }
}

# Save order_id and payment_id
export ORDER_ID="order-uuid"
export PAYMENT_ID="payment-uuid"
```

### Step 2.5: Mock Payment Success (Simulate User Completing Payment)

```bash
# In a real scenario, customer would visit the checkout_url and complete payment
# For demo, we simulate payment success via our mock webhook

curl -X POST http://localhost:8005/api/v1/webhooks/mock/ \
  -H "Content-Type: application/json" \
  -d "{
    \"payment_reference\": \"$PAYMENT_ID\",
    \"provider_payment_id\": \"ch_mock_12345\",
    \"status\": \"completed\",
    \"amount\": 8990000
  }"

# Response: Webhook acknowledged
{
  "success": true,
  "message": "Webhook processed successfully"
}

# Wait 1-2 seconds for processing...
sleep 2

# Check if order status updated
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8004/api/v1/orders/$ORDER_ID/

# Expected: Order status should be "confirmed" or "processing"
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "order_number": "ORD-20260411-123456",
    "status": "confirmed",  # ✅ Changed from "awaiting_payment"
    "payment_status": "completed",  # ✅ Changed
    "shipment_id": "shipment-uuid",  # ✅ Auto-created
    "paid_at": "2026-04-11T10:30:00Z"
  }
}
```

### Step 2.6: Check Shipment Created

```bash
SHIPMENT_ID="shipment-uuid-from-previous-response"

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/shipments/$SHIPMENT_ID/

# Response: Shipment tracking info
{
  "success": true,
  "data": {
    "id": "shipment-uuid",
    "shipment_reference": "SHIP-20260411-123456",
    "tracking_number": "1234567890ABC",
    "status": "created",
    "provider": "giao_mien_phi",
    "tracking_url": "https://tracking.giaomienphixyz/1234567890ABC",
    "items": [
      {
        "product_id": "prod-uuid",
        "product_name": "Samsung Galaxy S24",
        "quantity": 1
      }
    ]
  }
}
```

---

## DEMO FLOW #3: Shipment Tracking & Status Updates (5 min)

**Scenario:** Mock shipment progression through delivery

### Step 3.1: Mock Shipment Status Transitions

As admin, you can mock shipment status changes:

```bash
# Get mock shipments (admin only)
curl -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8008/api/v1/mock-shipments/

# Transition shipment to "in_transit"
curl -X POST \
  -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8008/api/v1/mock-shipments/$SHIPMENT_ID/transition/ \
  -H "Content-Type: application/json" \
  -d '{"new_status": "in_transit"}'

# Transition to "delivered"
curl -X POST \
  -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8008/api/v1/mock-shipments/$SHIPMENT_ID/transition/ \
  -H "Content-Type: application/json" \
  -d '{"new_status": "delivered"}'
```

### Step 3.2: Check Updated Order Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8004/api/v1/orders/$ORDER_ID/

# Response shows updated fulfillment_status
{
  "success": true,
  "data": {
    "order_number": "ORD-20260411-123456",
    "status": "delivered",  # ✅ Updated after shipment delivered
    "fulfillment_status": "fulfilled",
    "shipment_id": "shipment-uuid",
    "delivered_at": "2026-04-11T14:30:00Z"
  }
}
```

### Step 3.3: Chat Query for Order Status

```bash
# Ask AI about order status
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/ai/chat/ask/ \
  -d '{
    "session_id": "'$SESSION'",
    "message": "Đơn hàng của tôi đang ở đâu?"
  }'

# Response: AI pulls real order/shipment data
{
  "success": true,
  "data": {
    "chat_response": "Đơn hàng ORD-20260411-123456 của bạn đã được giao thành công. Bạn có thể theo dõi tại...",
    "order_info": {
      "order_number": "ORD-20260411-123456",
      "status": "delivered",
      "tracking_number": "1234567890ABC",
      "tracking_url": "https://..."
    }
  }
}
```

---

## DEMO FLOW #4: Admin Dashboard (5 min)

**Scenario:** Staff admin monitors orders, inventory, and catalog

### Step 4.1: List All Orders (Admin)

```bash
curl -H "Authorization: Bearer $(curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -d '{\"email\":\"admin@techshop.local\",\"password\":\"AdminPass123!\"}' \
  | jq -r '.data.access')" \
  http://localhost:8004/api/v1/orders/

# Or use internal admin key
curl -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8004/api/v1/admin/orders/?limit=10
```

### Step 4.2: Inventory Management

```bash
# List low-stock items
curl -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8007/api/v1/admin/inventory/stock-items/?low_stock=true

# Adjust stock
curl -X POST \
  -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8007/api/v1/admin/inventory/stock-items/{stock_id}/adjust/ \
  -H "Content-Type: application/json" \
  -d '{"quantity": 50, "reason": "Restock order received"}'
```

### Step 4.3: AI Analytics

```bash
# View behavioral insights
curl -H "X-Internal-Service-Key: internal-secret-key" \
  http://localhost:8000/api/v1/admin/ai/insights/

# View user preferences
curl -H "X-Internal-Service-Key: internal-secret-key" \
  "http://localhost:8000/api/v1/admin/ai/users?order_by=-purchase_intent_score&limit=5"
```

---

## TROUBLESHOOTING

### Services Won't Start

```bash
# Check logs
docker-compose logs user_service
docker-compose logs order_service

# Check database connectivity
docker-compose logs postgres

# Restart specific service
docker-compose restart order_service
```

### No Products Showing

```bash
# Run seed again
python shared/scripts/seed_complete_system.py --clean --verbose

# Verify products were created
curl http://localhost:8002/api/v1/catalog/products/ | jq '.data.count'
# Should show: 45 or more
```

### Payment Not Processing

```bash
# Check payment service logs
docker-compose logs payment_service

# Trigger mock payment manually
curl -X POST http://localhost:8005/api/v1/webhooks/mock/ \
  -d '... [see DEMO FLOW #2, Step 2.5]'
```

### Order Stuck in "awaiting_payment"

```bash
# Manually trigger payment success callback
ORDER_ID="your-order-id"
PAYMENT_ID="payment-id-from-order"

curl -X POST http://localhost:8005/api/v1/webhooks/mock/ \
  -H "Content-Type: application/json" \
  -d "{\"payment_id\": \"$PAYMENT_ID\", \"status\": \"completed\"}"
```

---

## PERFORMANCE TESTING

### Load Testing Orders

```bash
# Using Apache Bench or similar
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8004/api/v1/orders/

# Or use k6 (install: npm install -g k6)
k6 run --vus 10 --duration 30s shared/scripts/load_test_orders.js
```

### Database Query Performance

```bash
# Connect to product DB
psql postgresql://user:pass@localhost:5442/product_service

# Check indexes
\d+ products
\d+ categories

# Run query analysis
EXPLAIN ANALYZE SELECT * FROM catalog_product WHERE status='active' AND brand_id='...';
```

---

## KEY STATISTICS FOR DEMO

After running seed with defaults:

- **Users:** 4 (1 admin, 1 staff, 2 customers)
- **Products:** 45+ across 10 brands
- **Stock Items:** 200+ inventory entries
- **Orders:** 5 in various states (pending, paid, shipped, delivered, cancelled)
- **AI Events:** 60+ behavioral events
- **Shipments:** 4+ shipments in different statuses

### Demo Customer Journey

**John (Samsung enthusiast):**
- Searches: Samsung (5x)
- Clicks product: (10x Samsung, 2x others)
- Add to cart: (3x Samsung)
- Orders: 1 Samsung laptop ✅
- Expected recommendation: Samsung first place

**Jane (Diverse shopper):**
- Varied browsing
- Order: 1 MacBook
- Expected recommendation: Balanced mix

---

##TIMINGS FOR PRESENTATION

| Step | Duration | Notes |
|------|----------|-------|
| Setup (docker + seed) | 3-5 min | One-time |
| Demo Flow #1 (Browse) | 3 min | Snappy online browsing |
| Demo Flow #2 (Purchase) | 5 min | Shows full order lifecycle |
| Demo Flow #3 (Tracking) | 3 min | Shipment progression |
| Demo Flow #4 (Admin) | 2 min | Management dashboard |
| **TOTAL** | **~13 min** | **End-to-end demo** |

---

## NOTES FOR PRESENTERS

1. **Pre-demo:** Run `python shared/scripts/seed_complete_system.py` once to populate data
2. **Live demo:** Open browser/terminal and execute curl commands as shown
3. **Contingency:** Have API collection (`shared/postman/TechShop.postman_collection.json`) ready for clicking
4. **Backup:** If real demo fails, have screenshots/video ready
5. **Talking points:**
   - Microservices architecture (8 independent services)
   - End-to-end order workflow reliability
   - AI-powered personalization
   - Real inventory management
   - Event-driven AI learning

---

**Last Updated:** April 11, 2026  
**Next Review:** After production deployment
