# TechShop Seeding - Data Reference

Auto-generated reference of data created during seeding operations.

## How to Use This File

After running the seed script, this file will be populated with all created resource IDs for reference and verification.

## Users Created

| Email | ID | Role | Password |
|-------|----|----|----------|
| admin@example.com | `{admin_id}` | admin | admin123 |
| staff@example.com | `{staff_id}` | staff | staff123 |
| john@example.com | `{john_id}` | customer | john123 |
| jane@example.com | `{jane_id}` | customer | jane123 |

## Products Catalog

### Categories (12 total)

| ID | Name | Description |
|----|------|-------------|
| `{cat_1}` | Laptops | Computer laptops and notebooks |
| `{cat_2}` | Desktops | Desktop computers |
| `{cat_3}` | Phones | Mobile phones |
| `{cat_4}` | Tablets | Tablet devices |
| `{cat_5}` | Monitors | Display monitors |
| `{cat_6}` | Keyboards | Keyboards |
| `{cat_7}` | Mice | Computer mice |
| `{cat_8}` | Headphones | Audio headphones |
| `{cat_9}` | Printers | Printer devices |
| `{cat_10}` | Routers | Network routers |
| `{cat_11}` | Cameras | Digital cameras |
| `{cat_12}` | Speakers | Audio speakers |

### Brands (10 total)

- Samsung: `{samsung_brand_id}`
- Apple: `{apple_brand_id}`
- Nokia: `{nokia_brand_id}`
- Xiaomi: `{xiaomi_brand_id}`
- Asus: `{asus_brand_id}`
- Dell: `{dell_brand_id}`
- Sony: `{sony_brand_id}`
- LG: `{lg_brand_id}`
- Acer: `{acer_brand_id}`
- HP: `{hp_brand_id}`

### Sample Products (30-50 total)

| Product ID | Name | Brand | Price | Stock |
|------------|------|-------|-------|-------|
| `{prod_1}` | Galaxy Book Go | Samsung | 8,500,000 VND | 50 |
| `{prod_2}` | MacBook Air M1 | Apple | 24,900,000 VND | 20 |
| `{prod_3}` | XPS 13 | Dell | 22,000,000 VND | 20 |
| `{prod_4}` | Pavilion 15 | HP | 13,000,000 VND | 25 |
| `{prod_5}` | VivoBook 15 | Asus | 11,000,000 VND | 30 |

## Orders & Transactions

### Orders (5 total)

| Order ID | Order Number | Customer | Status | Total | Created |
|----------|-------------|----------|--------|-------|---------|
| `{order_1}` | ORD-20260411-000001 | john@example.com | PENDING | 8,500,000 | 2026-04-11 |
| `{order_2}` | ORD-20260411-000002 | jane@example.com | AWAITING_PAYMENT | 12,300,000 | 2026-04-11 |
| `{order_3}` | ORD-20260411-000003 | john@example.com | PAID | 24,900,000 | 2026-04-11 |
| `{order_4}` | ORD-20260411-000004 | jane@example.com | SHIPPED | 18,500,000 | 2026-04-11 |
| `{order_5}` | ORD-20260411-000005 | john@example.com | DELIVERED | 11,000,000 | 2026-04-10 |

### Carts (2 total)

| Cart ID | Owner | Status | Items |
|---------|-------|--------|-------|
| `{cart_1}` | john@example.com | Active | 1x Galaxy Book Go |
| `{cart_2}` | jane@example.com | Active | 2x different products |

### Payments (3-4 total)

| Payment ID | Order ID | Amount | Status | Created |
|-----------|----------|--------|--------|---------|
| `{payment_1}` | `{order_3}` | 24,900,000 VND | PAID | 2026-04-11 |
| `{payment_2}` | `{order_4}` | 18,500,000 VND | PAID | 2026-04-11 |
| `{payment_3}` | `{order_5}` | 11,000,000 VND | PAID | 2026-04-10 |

## AI Service Data

### Knowledge Documents (6 total)

| Doc ID | Title | Category |
|--------|-------|----------|
| `{ai_doc_1}` | Shipping Policy | shipping |
| `{ai_doc_2}` | Return Policy | returns |
| `{ai_doc_3}` | Payment Methods | payment |
| `{ai_doc_4}` | Warranty Information | warranty |
| `{ai_doc_5}` | Product Guide - Samsung Laptops | products |
| `{ai_doc_6}` | AI Recommendations | recommendations |

### Behavioral Events (30+ total)

#### John's Events (Samsung Preference)

- **Search Events**: 5
- **Product Clicks**: 10 (Samsung products)
- **Add to Cart**: 3 (Samsung products)
- **Order Created**: 1 (Samsung laptop)
- **Total**: ~25 events

#### Jane's Events (Diverse Browsing)

- **Product Views**: 8 (various brands)
- **Total**: ~8 events

**Total AI Events Created**: 33+

## Inventory Snapshot

### Out of Stock Items (2-3)

1. Galaxy Tab S7 (`{prod_tab1}`) - 0 units
2. Galaxy Tab S8 (`{prod_tab2}`) - 0 units

### Low Stock Items (2-3)

1. Another Product (`{prod_low1}`) - 3 units
2. Another Product (`{prod_low2}`) - 3 units

### Normal Stock

- Samsung products: 50 units each
- Apple products: 20 units each
- Other brands: 20-30 units each

## Quick Verification Commands

### Get All Users

```bash
curl -s http://localhost:8001/api/v1/internal/users/ \
  -H "X-Internal-Service-Key: internal-secret-key" | jq '.data.results[] | {id, email, role}'
```

### Get All Products with Stock

```bash
curl -s "http://localhost:8002/api/v1/internal/products/?limit=100" \
  -H "X-Internal-Service-Key: internal-secret-key" | \
  jq '.data.results[] | {id, name, price} | @csv' | head -20
```

### Get John's Orders

```bash
JOHN_ID="{john_id}"
curl -s "http://localhost:8004/api/v1/orders?user_id=$JOHN_ID" \
  -H "X-User-ID: $JOHN_ID" | \
  jq '.data[] | {order_number, status, total: .grand_total_amount}'
```

### Get John's AI Events

```bash
JOHN_ID="{john_id}"
curl -s "http://localhost:8000/api/v1/internal/ai/events/?user_id=$JOHN_ID" \
  -H "X-Internal-Service-Key: internal-secret-key" | \
  jq '.data | group_by(.event_type) | map({event_type: .[0].event_type, count: length})'
```

**Expected output**:
```json
[
  { "event_type": "product_search", "count": 5 },
  { "event_type": "product_click", "count": 10 },
  { "event_type": "add_to_cart", "count": 3 }
]
```

### Get AI Recommendations for John

```bash
JOHN_ID="{john_id}"
curl -s "http://localhost:8000/api/v1/recommendations?user_id=$JOHN_ID" \
  -H "X-User-ID: $JOHN_ID" | \
  jq '.data[] | {product_id, product_name, brand_name, rank: .recommendation_rank}' | head -5
```

**Expected output**:
```json
{
  "product_id": "{samsung_laptop_id}",
  "product_name": "Galaxy Book Go",
  "brand_name": "Samsung",
  "rank": 1
}
```

## Demo Scenario Status

### John's Samsung Journey

✓ Created user (john@example.com)
✓ Created 5 searches for "Samsung under 10 triệu"
✓ Created 10 clicks on Samsung products
✓ Created 3 add-to-cart events
✓ Created order with Samsung laptop (PAID status)
✓ AI learned Samsung preference
✓ Samsung appears first in recommendations

### Jane's Diverse Shopping

✓ Created user (jane@example.com)
✓ Created 8 views across different brands
✓ Created active cart with 2 different products
✓ Created order with diverse items
✓ AI has diverse recommendation set

## Statistics

| Metric | Value |
|--------|-------|
| Total Users | 4 |
| Total Categories | 12 |
| Total Brands | 10 |
| Total Products | 45 |
| Products with Stock | 42 |
| Out of Stock Products | 2 |
| Low Stock Products | 2 |
| Total Carts | 2 |
| Total Orders | 5 |
| PENDING Orders | 1 |
| AWAITING_PAYMENT Orders | 1 |
| PAID Orders | 1 |
| SHIPPED Orders | 1 |
| DELIVERED Orders | 1 |
| Total Payments | 3 |
| AI Knowledge Docs | 6 |
| Total AI Events | 33+ |
| Avg Events per User | 8+ |

## Troubleshooting

### Missing Data?

If expected counts don't match:

1. Check service logs:
   ```bash
   docker-compose logs -f <service_name>
   ```

2. Re-run seed script:
   ```bash
   python shared/scripts/seed_complete_system.py --verbose
   ```

3. Verify service health:
   ```bash
   docker-compose ps
   ```

### ID Mismatches?

If IDs don't match expected format:

1. Check if services are using old database schema
2. Run migrations:
   ```bash
   docker-compose exec <service> python manage.py migrate
   ```
3. Re-seed:
   ```bash
   python shared/scripts/seed_complete_system.py
   ```

---

**Last Updated**: April 11, 2026
**Seeding Script Version**: 1.0
**Status**: Reference Document
