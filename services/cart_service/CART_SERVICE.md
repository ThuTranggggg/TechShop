# Cart Service Architecture & Design

## Overview

The `cart_service` is a bounded context (per Domain-Driven Design) responsible for managing user shopping carts in the e-commerce system. It operates as a standalone microservice with its own database, APIs, and business logic.

**Important:** Cart service does NOT own product or inventory domains. product_service owns product data. inventory_service owns stock management. cart_service coordinates between them and maintains only the minimal cart-specific data needed for a stable user experience.

## Bounded Context

### What Cart Service Owns
- User's active shopping cart
- Cart items (product references + snapshots)
- Cart status lifecycle
- Price snapshots for display stability
- Minimal product/variant metadata cache for cart rendering

### What Cart Service Does NOT Own
- Product catalog (owned by product_service)
- Inventory/stock data (owned by inventory_service)
- User identity/auth (owned by user_service)
- Order fulfillment (owned by order_service)

### Data Isolation
- Cart has its own PostgreSQL database (cart_service_db)
- Never direct DB access to other services
- Communication via REST APIs only
- No shared tables or schemas

## Domain Model

### Entities

#### Cart (Aggregate Root)
```python
Cart
├── id: UUID
├── user_id: UUID
├── status: CartStatus (active|checked_out|abandoned|expired|merged)
├── currency: str
├── subtotal_amount: Decimal
├── total_quantity: int
├── item_count: int
├── items: List[CartItem]
└── timestamps
```

**Business Rules:**
- Exactly one active cart per user
- Checked out carts are immutable
- Aggregate root enforces consistency

#### CartItem (Entity)
```python
CartItem
├── id: UUID
├── cart_id: UUID (FK)
├── product_reference: ProductReference
├── quantity: Quantity
├── price_snapshot: Price
├── product_snapshot: ProductSnapshot
├── status: CartItemStatus
└── timestamps
```

**Business Rules:**
- Max one instance of each product per cart (duplicate product+variant blocked)
- Quantity always > 0
- Status tracks availability

### Value Objects

#### Quantity
- Always > 0
- Immutable
- Supports increase/decrease returning new instance

#### ProductReference
- Identifies a product by product_id + optional variant_id
- No inheritance of product ownership
- Just a reference

#### Price
- Decimal amount + currency
- Represents price snapshot at time of cart addition
- Supports line_total calculation

#### ProductSnapshot
- Minimal product metadata: name, slug, brand, category, thumbnail, SKU
- Captured at time of adding to cart
- Ensures stable display if product_service data changes
- NOT the source of truth (product_service is)

### Enums

**CartStatus:**
- ACTIVE: Current shopping cart
- CHECKED_OUT: Order placed, cart finalized
- ABANDONED: Cart abandoned (>30 days inactive)
- EXPIRED: Cart expired due to business policy
- MERGED: Carts merged (guest→user scenario)

**CartItemStatus:**
- AVAILABLE: In stock, good to checkout
- UNAVAILABLE: Generic unavailable
- OUT_OF_STOCK: Inventory exhausted
- LOW_STOCK: Warning level
- PRODUCT_INACTIVE: Product deleted/unpublished
- VARIANT_NOT_FOUND: Variant no longer exists

## Architecture Layers

### 1. Domain Layer (`domain/`)
**Philosophy:** Pure business logic, zero framework dependencies

**Files:**
- `enums.py` - CartStatus, CartItemStatus
- `value_objects.py` - Quantity, Price, ProductReference, ProductSnapshot
- `entities.py` - Cart, CartItem with all business rules
- `services.py` - CartDomainService for complex operations
- `repositories.py` - ABC repository contracts

**Key:** All invariants checked here. If it gets past domain, it's valid.

### 2. Application Layer (`application/`)
**Philosophy:** Use case orchestration, coordinatio n with infrastructure

**Files:**
- `dtos.py` - Request/Response DTOs, no business logic
- `services.py` - CartApplicationService with ~15 use cases
  - get_or_create_active_cart()
  - add_item_to_cart()
  - update_item_quantity()
  - remove_cart_item()
  - clear_cart()
  - refresh_cart()
  - validate_cart()
  - checkout_preview()
  - mark_checked_out()
  - etc.

**Responsibility:**
- Coordinate domain + infrastructure
- Call external services (product, inventory)
- Manage repository access
- Build responses

### 3. Infrastructure Layer (`infrastructure/`)
**Philosophy:** Implementation details - database, HTTP clients, external services

**Files:**
- `models.py` - Django ORM models (CartModel, CartItemModel)
- `repositories.py` - Django implementations of repository contracts
- `clients.py` - HTTP clients for product_service, inventory_service

**Key:** 
- Framework-specific code isolated here
- Easy to swap implementations
- Clients handle service communication

### 4. Presentation Layer (`presentation/`)
**Philosophy:** HTTP API layer - serializers, views, permissions, routing

**Files:**
- `serializers.py` - DRF serializers for request/response
- `permissions.py` - Custom permission classes
- `api.py` - ViewSets for customer and internal APIs
- `urls.py` - URL routing
- `admin.py` - Django admin configuration

## API Endpoints

### Customer-Facing APIs
- POST /api/v1/cart/items/ - Add item
- PATCH /api/v1/cart/items/{id}/quantity/ - Update quantity
- DELETE /api/v1/cart/itemsitems/{id}/ - Remove item
- POST /api/v1/cart/items/{id}/increase/ - Increase qty
- POST /api/v1/cart/items/{id}/decrease/ - Decrease qty
- POST /api/v1/cart/refresh/ - Refresh snapshots
- POST /api/v1/cart/validate/ - Validate cart
- POST /api/v1/cart/clear/ - Clear cart
- GET /api/v1/cart/current/ - Get current cart
- GET /api/v1/cart/summary/ - Get cart summary
- POST /api/v1/cart/checkout-preview/ - Preview checkout

### Internal (Service-to-Service) APIs
- GET /api/v1/internal/carts/users/{user_id}/active/ - Get active cart
- GET /api/v1/internal/carts/{cart_id}/ - Get cart by ID
- POST /api/v1/internal/carts/{cart_id}/mark-checked-out/ - Mark as checked out
- POST /api/v1/internal/carts/{cart_id}/checkout-payload/ - Get checkout payload

## Inter-Service Integration

### Product Service Client
```python
class ProductServiceClient:
    def get_product_snapshot(product_id, variant_id) -> Dict
    def validate_product_active(product_id, variant_id) -> bool
    def bulk_get_product_snapshots(items) -> Dict
```

**Usage:** When adding/refreshing items, fetch latest product metadata

### Inventory Service Client
```python
class InventoryServiceClient:
    def check_availability(items) -> Dict
    def get_product_availability(product_id) -> Dict
```

**Usage:** When adding/updating items, check stock levels

### Auth Strategy
- Currently: Header-based (X-User-ID for customers, X-Internal-Service-Key for services)
- Production: Integrate with auth_service / OAuth2
- See permissions.py for details

## Use Case Flows

### Add Item to Cart
```
1. Get/create active cart for user
2. Validate product_id, variant_id
3. Call product_service for snapshot
4. Call inventory_service check availability
5. If all valid, add to cart (or increase qty if exists)
6. Persist cart + item
7. Return updated cart
```

### Refresh Cart
```
1. Get active cart
2. For each item:
   a. Fetch latest snapshot from product_service
   b. Check availability from inventory_service
   c. Mark AVAILABLE or OUT_OF_STOCK based on result
   d. Update snapshot if changed
3. Save all changes
4. Return cart with refresh indicators
```

### Checkout Preview
```
1. Get active cart
2. Validate all items (availability, product active)
3. If any invalid, return issues
4. Build checkout payload:
   - all items with quantities/prices
   - totals
   - snapshots
5. Return payload ready for order_service
```

### Mark Checked Out (Internal)
```
1. Called by order_service after order placed
2. Verify cart exists
3. Change status to CHECKED_OUT
4. Lock cart (no further modifications allowed)
5. Return confirmation
```

## Database Schema

### CartModel
- id (UUID, PK)
- user_id (UUID, FK to user_service)
- status (VARCHAR, indexed)
- currency (VARCHAR)
- subtotal_amount (DECIMAL)
- total_quantity (BigInt)
- item_count (BigInt)
- timestamps
- **Constraints:** UNIQUE(user_id, status) WHERE status='active'

### CartItemModel
- id (UUID, PK)
- cart_id (UUID, FK to CartModel)
- product_id (UUID, FK to product_service)
- variant_id (UUID, nullable, FK to product_service)
- quantity (BigInt, ≥1)
- unit_price_snapshot (DECIMAL)
- currency (VARCHAR)
- product_name_snapshot (VARCHAR)
- product_slug_snapshot (VARCHAR)
- ... other snapshots (brand, category, SKU, thumbnail, attributes)
- status (VARCHAR)
- availability_checked_at (DateTime)
- timestamps
- **Constraints:** UNIQUE(cart_id, product_id, variant_id)

## Error Handling

Standard response format:
```json
{
  "success": false,
  "message": "Human-readable message",
  "errors": {...}
}
```

Common errors:
- Product not found: 404
- Insufficient inventory: 400
- Cart not found: 404
- Invalid quantity: 400
- Permission denied: 401/403
- Service unavailable: 503

## Testing

Test coverage:
- **Domain tests:** Value objects, entities, business rules
- **Model tests:** Django constraints, indexes, uniqueness
- **Repository tests:** CRUD operations, retrieval logic
- **Integration tests:** Full workflows

Run: `python manage.py test tests/`

## Deployment

### Database Setup
```bash
python manage.py migrate
```

### Seed Data (Dev)
```bash
python manage.py seed_carts
python manage.py seed_carts --clear  # Reset and reseed
```

### Local Development
```bash
python manage.py runserver 0.0.0.0:8003
```

### Production
```bash
gunicorn config.asgi:application --bind 0.0.0.0:8003
```

## Future Enhancements

### Phase 2
- Background job for abandoned cart detection
- Event publishing (new item added, quantity changed, etc.)
- Actual reservation creation on checkout (not just validation)

### Phase 3
- Guest cart support
- Cart merge (guest→authenticated user)
- Wishlist/saved items
- Coupon/promotion integration

### Phase 4
- Advanced analytics (cart abandonment patterns)
- Personalized recommendations
- Tax/shipping estimation
