# Cart Service - README

## Quick Start (5 minutes)

```bash
# 1. Setup environment
cd services/cart_service
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Seed demo data (optional)
python manage.py seed_carts

# 5. Create admin user (optional)
python manage.py createsuperuser

# 6. Start server
python manage.py runserver 0.0.0.0:8003
```

Service running at: `http://localhost:8003`

## Service Overview

**cart_service** manages shopping carts for authenticated users in the TechShop e-commerce platform. It is a bounded context that:

- ✅ Manages user shopping carts (add, remove, update items)
- ✅ Validates products via product_service
- ✅ Checks inventory via inventory_service
- ✅ Stores minimal product snapshots for stable UI display
- ✅ Prepares checkout with full validation
- ❌ Does NOT own products (product_service does)
- ❌ Does NOT manage inventory (inventory_service does)

## API Examples

### Get Current Cart
```bash
curl -X GET http://localhost:8003/api/v1/cart/current/ \
  -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000"
```

### Add Item to Cart
```bash
curl -X POST http://localhost:8003/api/v1/cart/items/ \
  -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "variant_id": null,
    "quantity": 2
  }'
```

### Checkout Preview
```bash
curl -X POST http://localhost:8003/api/v1/cart/checkout-preview/ \
  -H "X-User-ID: 550e8400-e29b-41d4-a716-446655440000"
```

## Architecture

**DDD (Domain-Driven Design) with 4 layers:**
- **Domain**: Pure business logic (entities, value objects, rules)
- **Application**: Use cases and orchestration
- **Infrastructure**: Database, HTTP clients
- **Presentation**: REST APIs, serializers, permissions

See [CART_SERVICE.md](CART_SERVICE.md) for full architecture documentation.

## Database Models

- **CartModel**: User's shopping cart with status and totals
- **CartItemModel**: Products in cart with snapshots and pricing

## Key Features

- ✅ Product snapshot for UI stability
- ✅ Price snapshot at add-time (not live)
- ✅ Inventory validation before add/update
- ✅ Checkout preview with full validation
- ✅ One active cart per user (database constraint)
- ✅ Immutable checked-out carts
- ✅ Inter-service clients for Product & Inventory

## Port Mapping
- Application: `localhost:8003`
- Database: `localhost:5435`
- Admin: `http://localhost:8003/admin/`
- API Docs: `http://localhost:8003/api/docs/`

## Environment Variables

Key variables in `.env.example`:
- `PRODUCT_SERVICE_URL=http://product_service:8006`
- `INVENTORY_SERVICE_URL=http://inventory_service:8007`
- `INTERNAL_SERVICE_KEY=your-internal-key`
- `UPSTREAM_TIMEOUT=5`

## Testing

```bash
python manage.py test tests/
```

Test coverage:
- Domain entities and value objects
- Django model constraints
- Repository operations
- Full integration workflows

## Management Commands

```bash
# Seed demo carts
python manage.py seed_carts

# Clear and reseed
python manage.py seed_carts --clear
```

## Documentation

- [CART_SERVICE.md](CART_SERVICE.md) - Architecture & Design
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was built
- [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) - Verification steps

## Support

- API Docs: http://localhost:8003/api/docs/
- Schema: http://localhost:8003/api/schema/
- Admin: http://localhost:8003/admin/
- `modules/cart/application`: commands, queries, application services
- `modules/cart/infrastructure`: ORM models, repository implementations, querysets
- `modules/cart/presentation`: API serializers/views/controllers
