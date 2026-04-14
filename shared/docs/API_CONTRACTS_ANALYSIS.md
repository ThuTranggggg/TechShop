# TechShop Microservices: API Contracts Analysis Report

**Generated:** April 11, 2026  
**Scope:** 8 Django Microservices in Monorepo  
**Purpose:** Identify API endpoint contracts, data models, serializers, inter-service communication, auth mechanisms, and potential integration mismatches

---

## Executive Summary

This report analyzes the API contracts across 8 microservices:
- **user_service** (Identity module)
- **product_service** (Catalog module)
- **inventory_service** (Inventory module)
- **cart_service** (Cart module)
- **order_service** (Order module)
- **payment_service** (Payment module)
- **shipping_service** (Shipping module)
- **ai_service** (AI module)

### Key Findings

**✓ Standardized Response Format:**
All services use a consistent envelope:
```json
{
  "success": true|false,
  "message": "...",
  "data": {...} || "errors": {...}
}
```

**⚠️ Authentication Heterogeneity:**
- Public services (user, product): No auth or role-based
- Internal endpoints: Use `X-Internal-Service-Key` header
- Customer-facing: JWT tokens or custom authentication

**⚠️ Integration Points with Potential Issues:**
- Cart → Order: Checkout payload structure mismatch risk
- Order → Inventory: Reservation/confirmation flow complexity
- Order → Payment: Async callback handling
- Various → AI: Event tracking format inconsistency

---

## Service Details

### 1. USER SERVICE (Identity Module)

**Base URL:** `http://user_service:8001`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| POST | `/api/v1/auth/register/` | Public | `{email, full_name, password, confirm_password, phone_number}` | `{id, email, full_name, ...}` | Register new user |
| POST | `/api/v1/auth/login/` | Public | `{email, password}` | `{access, refresh, user_info}` | JWT token login |
| POST | `/api/v1/auth/refresh/` | JWT | `{refresh}` | `{access}` | Refresh JWT token |
| POST | `/api/v1/auth/logout/` | JWT | `{}` | `{success}` | Invalidate token |
| GET | `/api/v1/auth/me/` | JWT | - | `{id, email, full_name, role, ...}` | Get current user profile |
| GET | `/api/v1/profile/` | JWT | - | User profile object | Get user profile |
| PATCH | `/api/v1/profile/update/` | JWT | `{full_name?, phone_number?, avatar_url?}` | Updated profile | Update profile |
| GET/POST | `/api/v1/profile/addresses/` | JWT | (POST) `{receiver_name, phone, line1, district, city, ...}` | Address list or created address | List/create addresses |
| GET/PATCH/DELETE | `/api/v1/profile/addresses/{id}/` | JWT | (PATCH) address fields | Address or success | Retrieve/update/delete address |
| POST | `/api/v1/profile/addresses/{id}/set-default/` | JWT | `{}` | Success response | Mark address as default |
| GET | `/api/v1/admin/users/` | Admin | `{page?, filters}` | `{count, results: [user]}` | List users (admin) |
| GET | `/api/v1/admin/users/detail/` | Admin | `?user_id=uuid` | User detail object | Get user by ID (admin) |
| PATCH | `/api/v1/admin/users/update/` | Admin | `{user_id, ...fields}` | Updated user | Update user (admin) |
| POST | `/api/v1/admin/users/deactivate/` | Admin | `{user_id}` | Success response | Deactivate user |
| POST | `/api/v1/admin/users/activate/` | Admin | `{user_id}` | Success response | Activate user |
| POST | `/api/v1/admin/users/change-role/` | Admin | `{user_id, new_role}` | Updated user | Change user role |
| GET | `/api/v1/admin/users/addresses/` | Admin | `?user_id=uuid` | Address array | Get user addresses |
| **INTERNAL** | `/api/v1/internal/users/get/` | Internal Key | `?user_id=uuid` | User object | Get user by ID (internal) |
| **INTERNAL** | `/api/v1/internal/users/bulk/` | Internal Key | `{user_ids: []}` | `{users: [...]}` | Bulk get users |
| **INTERNAL** | `/api/v1/internal/users/status/` | Internal Key | `?user_id=uuid` | `{user_id, is_active, ...}` | Get user status |
| **INTERNAL** | `/api/v1/internal/users/validate-active/` | Internal Key | `?user_id=uuid` | `{is_valid, is_active}` | Check if user is active |

#### Data Models

```
User
├── id: UUID (PK)
├── email: String (unique)
├── full_name: String
├── phone_number: String?
├── date_of_birth: Date?
├── avatar_url: URL?
├── role: Enum(CUSTOMER, STAFF, ADMIN)
├── is_active: Boolean
├── is_verified: Boolean
├── is_staff: Boolean (Django)
├── created_at: DateTime
├── updated_at: DateTime
└── last_login: DateTime

Address
├── id: UUID (PK)
├── user_id: UUID (FK)
├── receiver_name: String
├── phone_number: String
├── line1: String (street)
├── line2: String? (apt/suite)
├── ward: String?
├── district: String
├── city: String
├── country: String
├── postal_code: String?
├── address_type: Enum(HOME, OFFICE, OTHER)
├── is_default: Boolean (unique per user)
├── created_at: DateTime
└── updated_at: DateTime
```

#### Serializers

- `RegisterSerializer`: Validates email uniqueness, password strength, password confirmation
- `LoginSerializer`: Authenticates user credentials
- `CustomTokenObtainPairSerializer`: Returns JWT with custom claims (email, full_name, role)
- `UserProfileSerializer`: Read-only user info
- `UserProfileUpdateSerializer`: Allows updating full_name, phone_number, date_of_birth, avatar_url
- `AddressSerializer`: Full address with computed full_address property

#### Authentication

- **Public Endpoints:** No auth required
- **User Endpoints:** JWT Bearer token in `Authorization` header
- **Admin Endpoints:** Requires admin role in JWT claims
- **Internal Endpoints:** `X-Internal-Service-Key` header + optional `X-User-ID`

#### Response Format

```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "customer"
  }
}
```

#### Inter-Service Communication

No outbound calls to other services.

---

### 2. PRODUCT SERVICE (Catalog Module)

**Base URL:** `http://product_service:8006`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| GET | `/api/v1/catalog/products/` | Public | `{page?, search?, category?, brand?, min_price?, max_price?}` | `{count, results: [product]}` | List products with filters |
| GET | `/api/v1/catalog/products/{id}/` | Public | - | Product detail | Get product detail |
| GET | `/api/v1/catalog/products/{id}/variants/` | Public | - | `{variants: [...]}` | List product variants |
| GET | `/api/v1/catalog/products/{id}/media/` | Public | - | `{media: [...]}` | Get product media |
| GET | `/api/v1/catalog/products/trending/` | Public | - | `{products: [...]}` | Get trending products |
| GET | `/api/v1/catalog/categories/` | Public | - | `{results: [category]}` | List categories |
| GET | `/api/v1/catalog/brands/` | Public | - | `{results: [brand]}` | List brands |
| GET | `/api/v1/catalog/types/` | Public | - | `{results: [type]}` | List product types |
| POST | `/api/v1/catalog/products/` | Staff | Product data | Created product | Create product (staff) |
| PATCH | `/api/v1/catalog/products/{id}/` | Staff | Product fields | Updated product | Update product (staff) |
| DELETE | `/api/v1/catalog/products/{id}/` | Staff | - | Success | Delete product (staff) |
| POST | `/api/v1/catalog/products/{id}/variants/` | Staff | Variant data | Created variant | Create variant (staff) |
| POST | `/api/v1/catalog/products/{id}/media/` | Staff | Media data | Created media | Add media (staff) |
| POST | `/api/v1/catalog/products/{id}/publish/` | Staff | `{}` | Published product | Publish product (staff) |
| **INTERNAL** | `/api/v1/internal/products/{id}/snapshot/` | Internal Key | `?variant_id=uuid` | Product snapshot | Get product with live price/info |
| **INTERNAL** | `/api/v1/internal/products/{id}/validate/` | Internal Key | `?variant_id=uuid` | `{is_valid, is_active}` | Validate product is active |
| **INTERNAL** | `/api/v1/internal/products/snapshots/bulk/` | Internal Key | `{items: [{product_id, variant_id?}]}` | `{product_id: {...}}` | Bulk fetch snapshots |

#### Data Models

```
Category
├── id: UUID (PK)
├── name: String
├── slug: String (unique)
├── parent_id: UUID? (self-referential, prevent cycles)
├── description: Text
├── image_url: URL
├── is_active: Boolean
├── sort_order: Integer
├── created_at: DateTime
└── updated_at: DateTime

Brand
├── id: UUID (PK)
├── name: String
├── slug: String (unique)
├── description: Text
├── logo_url: URL
├── is_active: Boolean
├── created_at: DateTime
└── updated_at: DateTime

ProductType
├── id: UUID (PK)
├── code: String (unique)
├── name: String
├── description: Text
├── is_active: Boolean
├── created_at: DateTime
└── updated_at: DateTime

Product (Aggregate Root)
├── id: UUID (PK)
├── name: String
├── slug: String (unique)
├── short_description: String
├── description: Text
├── category_id: UUID (FK) [REQUIRED]
├── brand_id: UUID? (FK)
├── product_type_id: UUID (FK) [REQUIRED]
├── base_price: Decimal (max_digits=12, decimal_places=2)
├── currency: String (default: VND)
├── attributes: JSON (flexible)
├── status: Enum(DRAFT, ACTIVE, DISCONTINUED)
├── is_active: Boolean
├── is_featured: Boolean
├── thumbnail_url: URL
├── seo_title: String
├── seo_description: String
├── published_at: DateTime?
├── created_at: DateTime
└── updated_at: DateTime

ProductVariant
├── id: UUID (PK)
├── product_id: UUID (FK)
├── sku: String (unique)
├── name: String
├── attributes: JSON
├── price_override: Decimal?
├── is_active: Boolean
├── created_at: DateTime
└── updated_at: DateTime

ProductMedia
├── id: UUID (PK)
├── product_id: UUID (FK)
├── type: Enum(IMAGE, VIDEO)
├── url: URL
├── alt_text: String
├── is_primary: Boolean
├── sort_order: Integer
├── created_at: DateTime
└── updated_at: DateTime
```

#### Serializers

- `CategorySerializer`: Lists categories with children_count and products_count
- `BrandSerializer`: Lists brands with products_count
- `ProductTypeSerializer`: Lists product types with products_count
- `PublicProductSerializer`: Read-only, includes name, slug, price, description, media, category, brand
- `ProductDetailSerializer`: Extended with variants, media, attributes

#### Authentication

- **Public Endpoints:** No auth (anyone can browse)
- **Staff Endpoints:** Requires STAFF or ADMIN role
- **Internal Endpoints:** `X-Internal-Service-Key` header

#### Response Format

Same as user_service: `{success, message, data}`

#### Inter-Service Communication

**Called by:**
- Cart Service: Get product snapshots for display
- Order Service: Get product snapshots for order items
- Inventory Service: Validate product exists when creating stock items

**Snapshot Response Example:**
```json
{
  "success": true,
  "data": {
    "id": "product-uuid",
    "name": "Laptop Pro",
    "slug": "laptop-pro",
    "price": 1500.00,
    "currency": "USD",
    "brand": "TechBrand",
    "category": "Electronics",
    "thumbnail_url": "https://...",
    "attributes": {...},
    "is_active": true,
    "status": "active"
  }
}
```

---

### 3. INVENTORY SERVICE (Inventory Module)

**Base URL:** `http://inventory_service:8007`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| GET | `/api/v1/admin/inventory/stock-items/` | Admin | `{page?, product_id?, warehouse?}` | `{count, results: [stock]}` | List stock items |
| POST | `/api/v1/admin/inventory/stock-items/` | Admin | `{product_id, quantity, warehouse_code}` | Created stock item | Create stock item |
| PATCH | `/api/v1/admin/inventory/stock-items/{id}/` | Admin | `{on_hand_quantity?, safety_stock?}` | Updated stock item | Update stock |
| POST | `/api/v1/admin/inventory/stock-items/{id}/stock-in/` | Admin | `{quantity, reference_id?, note?}` | Updated stock | Stock in (receive) |
| POST | `/api/v1/admin/inventory/stock-items/{id}/stock-out/` | Admin | `{quantity, reference_id?, note?}` | Updated stock | Stock out (ship) |
| POST | `/api/v1/admin/inventory/stock-items/{id}/adjust/` | Admin | `{quantity, reason}` | Updated stock | Adjust stock |
| **INTERNAL** | `/api/v1/internal/inventory/check-availability/` | Internal Key | `{items: [{product_id, variant_id?, quantity}]}` | `{available: bool, items: [...]}` | Check if items available |
| **INTERNAL** | `/api/v1/internal/inventory/reserve/` | Internal Key | `{order_id, user_id, items: [...]}` | `{reservations: [{id, status, ...}]}` | Reserve stock for order |
| **INTERNAL** | `/api/v1/internal/inventory/confirm/` | Internal Key | `{order_id, reservation_ids: [...]}` | Success response | Confirm reservation (after payment) |
| **INTERNAL** | `/api/v1/internal/inventory/release/` | Internal Key | `{order_id, reservation_ids, reason}` | Success response | Release reservation (on failure) |
| **INTERNAL** | `/api/v1/internal/inventory/products/{id}/availability/` | Internal Key | - | Availability info | Get product availability |

#### Data Models

```
StockItem (Aggregate Root)
├── id: UUID (PK)
├── product_id: UUID (FK from product_service)
├── variant_id: UUID?
├── sku: String?
├── warehouse_code: String (default: MAIN)
├── on_hand_quantity: BigInt (≥ 0)
├── reserved_quantity: BigInt (≥ 0, ≤ on_hand)
├── safety_stock: BigInt (≥ 0)
├── is_active: Boolean
├── created_at: DateTime
├── updated_at: DateTime
├── [Computed] available_quantity = on_hand - reserved
└── [Constraints]
    ├── unique(product_id, variant_id, warehouse_code)
    ├── on_hand ≥ 0
    ├── reserved ≥ 0
    └── reserved ≤ on_hand

StockReservation (Entity)
├── id: UUID (PK)
├── reservation_code: String (unique, for idempotency)
├── stock_item_id: UUID (FK)
├── product_id: UUID
├── variant_id: UUID?
├── order_id: UUID? (reference only)
├── cart_id: UUID? (reference only)
├── user_id: UUID?
├── quantity: BigInt (≥ 1)
├── status: Enum(ACTIVE, CONFIRMED, RELEASED, EXPIRED)
├── expires_at: DateTime
├── metadata: JSON
├── created_at: DateTime
└── updated_at: DateTime

StockMovement (Audit Trail)
├── id: UUID (PK)
├── stock_item_id: UUID (FK)
├── product_id: UUID
├── movement_type: Enum(STOCK_IN, STOCK_OUT, ADJUSTMENT, RESERVATION, CONFIRMATION, RELEASE)
├── quantity: BigInt
├── reference_type: String?
├── reference_id: String?
├── note: Text?
└── created_at: DateTime
```

#### Serializers

- `StockItemSerializer`: Includes computed available_quantity and is_in_stock, is_low_stock methods
- `CreateReservationSerializer`: Validates product_id, quantity, optional expires_in_minutes
- `CheckAvailabilitySerializer`: Array of items with product_id, variant_id, quantity
- `AvailabilityResultSerializer`: Returns per-product availability details
- `StockReservationDetailSerializer`: Full reservation with status and expiry

#### Authentication

- **Admin Endpoints:** Requires ADMIN role
- **Internal Endpoints:** `X-Internal-Service-Key` header

#### Response Format

Same envelope: `{success, message, data}`

#### Reservation Flow

**Order → Inventory Reservation:**

1. Order Service calls: `POST /api/v1/internal/inventory/reserve/`
   ```json
   {
     "order_id": "order-uuid",
     "user_id": "user-uuid",
     "items": [
       {"product_id": "prod-uuid", "variant_id": null, "quantity": 2},
       {"product_id": "prod-uuid-2", "variant_id": "var-uuid", "quantity": 1}
     ]
   }
   ```

2. **Response (Success):**
   ```json
   {
     "success": true,
     "data": {
       "reservations": [
         {"id": "res-id-1", "status": "ACTIVE", "expires_at": "2026-04-12T..."},
         {"id": "res-id-2", "status": "ACTIVE", "expires_at": "2026-04-12T..."}
       ]
     }
   }
   ```

3. After payment succeeds, Order calls: `POST /api/v1/internal/inventory/confirm/`
   ```json
   {
     "order_id": "order-uuid",
     "reservation_ids": ["res-id-1", "res-id-2"]
   }
   ```

4. On payment failure, Order calls: `POST /api/v1/internal/inventory/release/`
   ```json
   {
     "order_id": "order-uuid",
     "reservation_ids": ["res-id-1", "res-id-2"],
     "reason": "Payment failed"
   }
   ```

#### Inter-Service Communication

**Called by:**
- Order Service: Reserve stock, confirm/release after payment
- Cart Service: Check product availability

**Called to:**
- None

---

### 4. CART SERVICE (Cart Module)

**Base URL:** `http://cart_service:8003`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| GET | `/api/v1/cart/` | JWT | - | Cart object | Get current user cart |
| POST | `/api/v1/cart/items/` | JWT | `{product_id, variant_id?, quantity}` | Updated cart | Add item to cart |
| PATCH | `/api/v1/cart/items/{item_id}/` | JWT | `{new_quantity}` | Updated cart | Update item quantity |
| DELETE | `/api/v1/cart/items/{item_id}/` | JWT | - | Updated cart | Remove item from cart |
| POST | `/api/v1/cart/items/{item_id}/increase/` | JWT | `{amount?}` | Updated cart | Increase item quantity |
| POST | `/api/v1/cart/items/{item_id}/decrease/` | JWT | `{amount?}` | Updated cart | Decrease item quantity |
| DELETE | `/api/v1/cart/` | JWT | - | Success | Clear entire cart |
| GET | `/api/v1/cart/validate/` | JWT | - | `{is_valid, issues: [...]}` | Validate cart items exist |
| POST | `/api/v1/cart/checkout-preview/` | JWT | - | `{is_valid, cart, issues, checkout_payload}` | Get checkout preview |
| **INTERNAL** | `/api/v1/internal/carts/{id}/validate/` | Internal Key | - | Validated cart | Validate cart from order |
| **INTERNAL** | `/api/v1/internal/carts/{id}/checkout-payload/` | Internal Key | - | `{items: [...], subtotal, ...}` | Build order creation payload |
| **INTERNAL** | `/api/v1/internal/carts/{id}/mark-checked-out/` | Internal Key | - | Success | Mark cart as checked out |

#### Data Models

```
Cart (Aggregate Root)
├── id: UUID (PK)
├── user_id: UUID (FK from user_service)
├── status: Enum(ACTIVE, CHECKED_OUT, ABANDONED)
├── currency: String (default: USD)
├── subtotal_amount: Decimal
├── total_quantity: BigInt
├── item_count: BigInt
├── last_activity_at: DateTime
├── created_at: DateTime
├── updated_at: DateTime
└── [Constraint] unique(user_id) where status=ACTIVE

CartItem (Entity)
├── id: UUID (PK)
├── cart_id: UUID (FK)
├── product_id: UUID (reference from product_service)
├── variant_id: UUID?
├── quantity: BigInt (≥ 1)
├── unit_price_snapshot: Decimal
├── currency: String
├── product_name_snapshot: String
├── product_slug_snapshot: String
├── variant_name_snapshot: String?
├── brand_name_snapshot: String?
├── category_name_snapshot: String?
├── sku: String?
├── thumbnail_url_snapshot: URL?
├── attributes_snapshot: JSON
├── status: Enum(AVAILABLE, UNAVAILABLE, OUT_OF_STOCK)
├── availability_checked_at: DateTime?
├── created_at: DateTime
└── updated_at: DateTime
```

#### Serializers

- `AddItemToCartSerializer`: Validates product_id, quantity ≥ 1
- `UpdateCartItemSerializer`: Validates new_quantity ≥ 1
- `CartItemSerializer`: Includes snapshot fields for stable display
- `CartSerializer`: Full cart with items, totals
- `CheckoutPreviewSerializer`: Includes validation issues and checkout_payload
- `CartValidationResultSerializer`: is_valid flag with array of issues

#### Authentication

- **Customer Endpoints:** JWT Bearer token, owns cart via header `X-User-ID`
- **Internal Endpoints:** `X-Internal-Service-Key` header

#### Response Format

Same: `{success, message, data}`

#### Checkout Payload Structure

Used by order_service when creating order from cart:

```json
{
  "items": [
    {
      "product_id": "uuid",
      "variant_id": "uuid?",
      "quantity": 2,
      "unit_price": "1500.00",
      "product_name": "Laptop Pro",
      "brand": "TechBrand",
      "category": "Electronics",
      "sku": "SKU123"
    }
  ],
  "subtotal": "3000.00",
  "currency": "USD",
  "total_quantity": 2,
  "item_count": 1
}
```

#### Inter-Service Communication

**Called by:**
- Order Service: Validate cart, get checkout payload, mark checked out

**Calls to:**
- Product Service: Get product snapshots for display
- Inventory Service: Check product availability

---

### 5. ORDER SERVICE (Order Module)

**Base URL:** `http://order_service:8003`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| GET | `/api/v1/orders/` | JWT | `{page?, status?, date_from?, date_to?}` | `{count, results: [order]}` | List user orders |
| GET | `/api/v1/orders/{id}/` | JWT | - | Full order detail | Get order detail |
| POST | `/api/v1/orders/` | JWT | Create order payload | Created order | Create order from cart |
| PATCH | `/api/v1/orders/{id}/` | JWT | `{notes?, shipping_address?}` | Updated order | Update order (before payment) |
| POST | `/api/v1/orders/{id}/cancel/` | JWT | `{reason?}` | Cancelled order | Cancel order |
| GET | `/api/v1/orders/{id}/timeline/` | JWT | - | `{status_history: []}` | Get order timeline |
| GET | `/api/v1/orders/{id}/invoice/` | JWT | - | PDF or JSON | Get invoice |
| **INTERNAL** | `/api/v1/internal/orders/{id}/shipment-created/` | Internal Key | `{shipment_id, shipment_ref, tracking_num, tracking_url?}` | Success | Notify shipment created |
| **INTERNAL** | `/api/v1/internal/orders/{id}/shipment-status-updated/` | Internal Key | `{shipment_id, status, location?}` | Success | Update shipment status |
| **INTERNAL** | `/api/v1/internal/orders/{id}/shipment-delivered/` | Internal Key | `{shipment_id, delivered_at}` | Success | Notify shipment delivered |
| **INTERNAL** | `/api/v1/internal/orders/{id}/shipment-failed/` | Internal Key | `{shipment_id, failure_reason}` | Success | Notify shipment failure |
| **INTERNAL** | `/api/v1/internal/orders/payment-success/` | Internal Key | `{order_id, payment_id, payment_reference}` | Success | Confirm payment success |
| **INTERNAL** | `/api/v1/internal/orders/payment-failed/` | Internal Key | `{order_id, payment_id, failure_reason}` | Success | Handle payment failure |

#### Data Models

```
Order (Aggregate Root)
├── id: UUID (PK)
├── order_number: String (human-readable: ORD-YYYYMMDD-XXXXXX)
├── user_id: UUID (FK from user_service)
├── cart_id: UUID? (reference only)
├── status: Enum(PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
├── payment_status: Enum(UNPAID, PENDING, COMPLETED, FAILED, REFUNDED)
├── fulfillment_status: Enum(UNFULFILLED, PARTIALLY_FULFILLED, FULFILLED, CANCELLED)
├── currency: String (default: VND)
├── Pricing
│  ├── subtotal_amount: Decimal
│  ├── shipping_fee_amount: Decimal
│  ├── discount_amount: Decimal
│  ├── tax_amount: Decimal
│  └── grand_total_amount: Decimal
├── Quantities
│  ├── total_quantity: Int
│  └── item_count: Int
├── Customer Snapshot
│  ├── customer_name_snapshot: String
│  ├── customer_email_snapshot: String
│  └── customer_phone_snapshot: String
├── Shipping Address Snapshot
│  ├── receiver_name: String
│  ├── receiver_phone: String
│  ├── shipping_line1: String
│  ├── shipping_line2: String?
│  ├── shipping_ward: String?
│  ├── shipping_district: String
│  ├── shipping_city: String
│  ├── shipping_country: String
│  └── shipping_postal_code: String?
├── Service References
│  ├── payment_id: UUID?
│  ├── payment_reference: String?
│  ├── shipment_id: UUID?
│  ├── shipment_reference: String?
│  └── stock_reservation_refs: JSON (array)
├── Milestones
│  ├── placed_at: DateTime?
│  ├── paid_at: DateTime?
│  ├── cancelled_at: DateTime?
│  └── completed_at: DateTime?
├── created_at: DateTime
└── updated_at: DateTime

OrderItem (Entity)
├── id: UUID (PK)
├── order_id: UUID (FK)
├── product_id: UUID (reference from product_service)
├── variant_id: UUID?
├── sku: String?
├── quantity: Int
├── unit_price: Decimal (frozen at purchase time)
├── line_total: Decimal (quantity × unit_price)
├── currency: String
├── Product Snapshot
│  ├── product_name_snapshot: String
│  ├── product_slug_snapshot: String
│  ├── variant_name_snapshot: String?
│  ├── brand_name_snapshot: String?
│  ├── category_name_snapshot: String?
│  ├── thumbnail_url_snapshot: URL?
│  └── attributes_snapshot: JSON
├── created_at: DateTime
└── updated_at: DateTime

OrderStatusHistory (Audit)
├── id: UUID (PK)
├── order_id: UUID (FK)
├── from_status: String?
├── to_status: String
├── note: Text
├── changed_by: UUID? (admin user)
└── created_at: DateTime
```

#### Serializers

- `OrderItemSerializer`: Includes product snapshot fields
- `OrderTotalsSerializer`: Pricing breakdown
- `AddressSnapshotSerializer`: Shipping address fields
- `OrderDetailSerializer`: Full order with items, totals, addresses
- `OrderListItemSerializer`: Summary for list (id, number, status, total, date)
- `CreateOrderFromCartSerializer`: Validates cart_id, shipping_address required fields
- `StatusHistoryItemSerializer`: Status transitions
- `CancelOrderSerializer`: Reason for cancellation

#### Authentication

- **Customer Endpoints:** JWT token (owns order via user_id)
- **Admin Endpoints:** Admin role required
- **Internal Endpoints:** `X-Internal-Service-Key` header

#### Response Format

Same: `{success, message, data}`

#### Create Order Flow

```
POST /api/v1/orders/
{
  "cart_id": "cart-uuid",
  "shipping_address": {
    "receiver_name": "John Doe",
    "receiver_phone": "+84123456789",
    "line1": "123 Main St",
    "district": "District 1",
    "city": "Ho Chi Minh",
    "country": "Vietnam",
    "line2": "Apt 4B",
    "ward": "Ward 5",
    "postal_code": "700000"
  },
  "notes": "Please deliver in morning"
}
```

**Order Service Internal Flow:**

1. Validate cart with Cart Service
2. Get checkout payload from Cart Service
3. Create Order in PENDING status
4. Reserve stock via Inventory Service
5. Create Payment via Payment Service
6. Mark cart as CHECKED_OUT
7. Return order with payment info

#### Inter-Service Communication

**Calls to:**
- Cart Service: `validate_cart()`, `build_checkout_payload()`, `mark_cart_checked_out()`
- Inventory Service: `create_reservations()`, `confirm_reservations()`, `release_reservations()`
- Payment Service: `create_payment()`
- Shipping Service: `create_shipment()` (after payment)
- AI Service: POST event about order creation

**Called by:**
- Payment Service: `payment-success`, `payment-failed` callbacks
- Shipping Service: Shipment status update callbacks

---

### 6. PAYMENT SERVICE (Payment Module)

**Base URL:** `http://payment_service:8005`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| POST | `/api/v1/payments/` | JWT | `{order_id, amount, currency, provider, method, description, return_url, cancel_url, success_url}` | Created payment | Create payment request |
| GET | `/api/v1/payments/{id}/` | JWT | - | Payment detail | Get payment status |
| PATCH | `/api/v1/payments/{id}/` | JWT | `{status?}` | Updated payment | Update payment |
| DELETE | `/api/v1/payments/{id}/` | JWT | - | Success | Cancel payment |
| POST | `/api/v1/payments/{id}/retry/` | JWT | `{}` | Retried payment | Retry payment |
| GET | `/api/v1/payments/by-reference/{ref}/` | JWT | - | Payment detail | Get by reference |
| POST | `/api/v1/webhooks/stripe/` | Public | Webhook payload | `{success: true}` | Stripe webhook callback |
| POST | `/api/v1/webhooks/mock/` | Public | Mock payload | `{success: true}` | Mock payment callback |
| **INTERNAL** | `/api/v1/internal/payments/create/` | Internal Key | `{order_id, user_id, amount, currency, order_number, metadata?}` | Created payment | Create payment (order service) |
| **INTERNAL** | `/api/v1/internal/payments/{id}/` | Internal Key | - | Payment detail | Get payment (internal) |

#### Data Models

```
Payment (Aggregate Root)
├── id: UUID (PK)
├── payment_reference: String (unique: PAY-YYYYMMDD-XXXXXX)
├── order_id: UUID (FK from order_service)
├── order_number: String? (snapshot)
├── user_id: UUID? (FK from user_service)
├── amount: Decimal
├── currency: String (enum)
├── provider: String (enum: STRIPE, MOCK, PAYPAL, VNPAY)
├── method: String (enum: CARD, BANK_TRANSFER, E_WALLET, MOCK)
├── status: Enum(CREATED, PROCESSING, PENDING, COMPLETED, FAILED, CANCELLED, EXPIRED)
├── Provider References
│  ├── provider_payment_id: String? (unique, from external provider)
│  ├── checkout_url: URL?
│  └── client_secret: String?
├── Descriptive
│  ├── description: Text
│  └── failure_reason: Text?
├── Return URLs
│  ├── return_url: URL?
│  ├── cancel_url: URL?
│  └── success_url: URL?
├── Milestones
│  ├── requested_at: DateTime
│  ├── completed_at: DateTime?
│  ├── failed_at: DateTime?
│  ├── cancelled_at: DateTime?
│  └── expired_at: DateTime?
├── metadata: JSON (extensibility)
├── created_at: DateTime
└── updated_at: DateTime

PaymentTransaction (Audit)
├── id: UUID (PK)
├── payment_id: UUID (FK)
├── type: Enum(AUTHORIZATION, CAPTURE, REFUND, CHARGEBACK, RETRY)
├── status: Enum(PENDING, SUCCESS, FAILED)
├── amount: Decimal
├── provider_transaction_id: String?
├── description: Text
├── created_at: DateTime
└── updated_at: DateTime
```

#### Serializers

- `CreatePaymentSerializer`: Validates all required fields
- `PaymentDetailSerializer`: Full payment info with status and URLs
- `PaymentStatusSerializer`: Minimal status info
- `PaymentWebhookSerializer`: Handles provider webhook payloads

#### Authentication

- **Customer Endpoints:** JWT token (user_id from token)
- **Internal Endpoints:** `X-Internal-Service-Key` header
- **Webhook Endpoints:** Public, but validated with provider signature

#### Response Format

Same: `{success, message, data}`

#### Payment Creation Flow

**From Order Service:**

```
POST /api/v1/internal/payments/create/
{
  "order_id": "order-uuid",
  "user_id": "user-uuid",
  "amount": "3000.00",
  "currency": "VND",
  "order_number": "ORD-20260411-123456",
  "metadata": {...}
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "payment-uuid",
    "payment_reference": "PAY-20260411-123456",
    "status": "CREATED",
    "checkout_url": "https://checkout.provider.com/...",
    "client_secret": "...",
    "amount": "3000.00",
    "currency": "VND"
  }
}
```

#### Webhook Callback Flow

After payment provider processes payment, it calls:

```
POST /api/v1/webhooks/stripe/ OR /api/v1/webhooks/mock/
{
  "payment_reference": "PAY-20260411-123456",
  "provider_payment_id": "ch_...",
  "status": "completed",
  "amount": "3000.00"
}
```

Payment Service then calls back to Order Service:

```
POST http://order_service:8003/api/v1/internal/orders/{order_id}/payment-success/
{
  "payment_id": "payment-uuid",
  "payment_reference": "PAY-20260411-123456"
}
```

#### Inter-Service Communication

**Called by:**
- Order Service: Create payment after order

**Calls to:**
- Order Service: Payment success/failure callbacks

---

### 7. SHIPPING SERVICE (Shipping Module)

**Base URL:** `http://shipping_service:8008`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| GET | `/api/v1/shipments/` | JWT | `{page?, status?, order_id?}` | `{count, results: [shipment]}` | List shipments |
| GET | `/api/v1/shipments/{id}/` | JWT | - | Shipment detail | Get shipment |
| GET | `/api/v1/shipments/{id}/tracking/` | JWT | - | Tracking info | Get tracking info |
| POST | `/api/v1/shipments/{id}/cancel/` | JWT | `{reason?}` | Cancelled shipment | Cancel shipment |
| GET | `/api/v1/mock-shipments/` | Admin | - | Mock shipments | List mock shipments |
| POST | `/api/v1/mock-shipments/` | Admin | Mock shipment data | Created mock shipment | Create mock shipment |
| POST | `/api/v1/mock-shipments/{id}/transition/` | Admin | `{new_status}` | Updated shipment | Transition mock shipment |
| **INTERNAL** | `/api/v1/internal/shipments/` | Internal Key | `{order_id, user_id, items, shipping_address, ...}` | Created shipment | Create shipment (order service) |
| **INTERNAL** | `/api/v1/internal/shipments/{id}/` | Internal Key | - | Shipment detail | Get shipment (internal) |
| **INTERNAL** | `/api/v1/internal/shipments/{id}/cancel/` | Internal Key | `{reason?}` | Cancelled shipment | Cancel shipment (internal) |

#### Data Models

```
Shipment (Aggregate Root)
├── id: UUID (PK)
├── shipment_reference: String (unique: SHIP-YYYYMMDD-XXXXXX)
├── tracking_number: String (unique)
├── order_id: UUID (FK from order_service)
├── order_number: String (snapshot)
├── user_id: UUID?
├── Provider & Service
│  ├── provider: Enum(MOCK, GIAO_MIEN_PHI, J&T, VIETTEL, NHATTIN)
│  └── service_level: Enum(STANDARD, EXPRESS, OVERNIGHT)
├── Status
│  ├── status: Enum(CREATED, PICKED_UP, IN_TRANSIT, DELIVERED, FAILED, CANCELLED)
│  └── failure_reason: Text?
├── Tracking
│  ├── tracking_url: URL?
│  ├── label_url: URL?
│  └── carrier_shipment_id: String?
├── Package Info
│  ├── package_count: Int (default: 1)
│  ├── package_weight: Decimal? (kg)
│  └── shipping_fee_amount: Decimal?
├── Delivery Timeline
│  ├── expected_pickup_at: DateTime?
│  ├── expected_delivery_at: DateTime?
│  ├── shipped_at: DateTime?
│  ├── delivered_at: DateTime?
│  └── cancelled_at: DateTime?
├── Receiver Address Snapshot
│  ├── receiver_name: String
│  ├── receiver_phone: String
│  ├── address_line1: String
│  ├── address_line2: String?
│  ├── ward: String?
│  ├── district: String
│  ├── city: String
│  ├── country: String
│  └── postal_code: String?
├── metadata: JSON
├── created_at: DateTime
└── updated_at: DateTime

ShipmentItem (Entity)
├── id: UUID (PK)
├── shipment_id: UUID (FK)
├── order_item_id: UUID? (reference from order_service)
├── product_id: UUID
├── quantity: Int
└── Product Snapshot
   ├── product_name: String
   ├── sku: String?
   └── unit_price: Decimal

ShipmentTrackingEvent (Audit)
├── id: UUID (PK)
├── shipment_id: UUID (FK)
├── event_type: Enum(CREATED, PICKED_UP, DISPATCH, IN_TRANSIT, DELIVERED, FAILED, EXCEPTION)
├── location: String?
├── description: Text?
├── timestamp: DateTime
└── metadata: JSON
```

#### Serializers

- `ShipmentSerializer`: Full shipment info with status, tracking, address
- `ShipmentCreateSerializer`: Requires order_id, user_id, items, shipping_address
- `ShipmentDetailSerializer`: Extended with tracking history
- `TrackingEventSerializer`: Event with location and description
- `ShipmentCancelSerializer`: Reason for cancellation

#### Authentication

- **Customer Endpoints:** JWT token (user_id from token)
- **Admin Endpoints:** Admin role
- **Mock Endpoints:** Admin role
- **Internal Endpoints:** `X-Internal-Service-Key` header

#### Response Format

Same: `{success, message, data}`

#### Shipment Creation Flow

**From Order Service (after payment success):**

```
POST /api/v1/internal/shipments/
{
  "order_id": "order-uuid",
  "order_number": "ORD-20260411-123456",
  "user_id": "user-uuid",
  "items": [
    {
      "order_item_id": "item-uuid",
      "product_id": "prod-uuid",
      "quantity": 2,
      "product_name": "Laptop Pro",
      "sku": "SKU123",
      "unit_price": "1500.00"
    }
  ],
  "shipping_address": {
    "receiver_name": "John Doe",
    "receiver_phone": "+84123456789",
    "address_line1": "123 Main St",
    "district": "District 1",
    "city": "Ho Chi Minh",
    "country": "Vietnam"
  },
  "provider": "GIAO_MIEN_PHI",
  "service_level": "STANDARD"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "shipment-uuid",
    "shipment_reference": "SHIP-20260411-123456",
    "tracking_number": "1234567890",
    "status": "CREATED",
    "tracking_url": "https://...",
    "label_url": "https://..."
  }
}
```

#### Status Update Flow

Mock provider (or real webhook) transitions status:

```
POST /api/v1/mock-shipments/{id}/transition/
{
  "new_status": "PICKED_UP"
}
```

Shipping Service then notifies Order Service:

```
POST http://order_service:8003/api/v1/internal/orders/{order_id}/shipment-status-updated/
{
  "shipment_id": "shipment-uuid",
  "shipment_reference": "SHIP-20260411-123456",
  "status": "PICKED_UP"
}
```

#### Inter-Service Communication

**Calls to:**
- Order Service: Shipment created, status updated, delivered, failed callbacks

**Called by:**
- Order Service: Create shipment after payment success

---

### 8. AI SERVICE (AI Module)

**Base URL:** `http://ai_service:8000`

#### Endpoints

| Method | Path | Auth | Input | Output | Purpose |
|--------|------|------|-------|--------|---------|
| POST | `/api/v1/ai/events/track/` | Public? | Event data | Success | Track single event |
| POST | `/api/v1/ai/events/bulk/` | Public? | `{events: [...]}` | Success | Bulk track events |
| POST | `/api/v1/internal/ai/events/` | Internal Key | `{events: [...]}` | Success | Bulk events (internal) |
| GET | `/api/v1/ai/users/{id}/preferences/` | JWT | - | Preference summary | Get user preferences |
| POST | `/api/v1/admin/ai/users/{id}/rebuild-profile/` | Admin | `{}` | Success | Rebuild user profile |
| GET | `/api/v1/ai/recommendations/` | JWT | `{limit?, mode?}` | `{products: [...]}` | Get recommendations |
| POST | `/api/v1/ai/chat/sessions/` | JWT | `{title?}` | Created session | Start chat session |
| GET | `/api/v1/ai/chat/sessions/` | JWT | `{page?}` | Sessions list | List chat sessions |
| GET | `/api/v1/ai/chat/sessions/{id}/` | JWT | - | Session detail | Get session detail |
| POST | `/api/v1/ai/chat/ask/` | JWT | `{session_id, message}` | `{response, message_id}` | Ask question in chat |
| GET | `/api/v1/ai/chat/messages/` | JWT | `{session_id, page?}` | Messages list | Get chat messages |
| POST/GET | `/api/v1/admin/ai/knowledge/` | Admin | (POST) knowledge doc | Created/list docs | Manage knowledge docs |
| GET | `/api/v1/admin/ai/knowledge/{id}/` | Admin | - | Knowledge doc detail | Get knowledge doc |

#### Data Models

```
BehavioralEvent (Immutable Log)
├── id: UUID (PK)
├── event_type: Enum(SEARCH, PRODUCT_VIEW, PRODUCT_CLICK, ADD_TO_CART, REMOVE_FROM_CART, CHECKOUT_STARTED, ORDER_CREATED, PAYMENT_SUCCESS, CHAT_QUERY, ...)
├── user_id: UUID? (null for anonymous)
├── session_id: String? (browser session)
├── product_id: UUID? (if applicable)
├── variant_id: UUID?
├── brand_name: String?
├── category_name: String?
├── price_amount: Decimal?
├── price_range: Enum(BUDGET, MID_RANGE, PREMIUM, LUXURY)?
├── keyword: String? (for searches)
├── source_service: String? (which service emitted)
├── occurred_at: DateTime (event time, not creation time)
├── metadata: JSON
├── created_at: DateTime (record time)
└── [Indexes] event_type, user_id, created_at, product_id, brand_name, category_name

UserPreferenceProfile
├── id: UUID (PK)
├── user_id: UUID (unique)
├── preferred_brands: JSON (list of {brand: string, score: float})
├── preferred_categories: JSON (list of {category: string, score: float})
├── preferred_price_ranges: JSON (list of {range: string, score: float})
├── recent_keywords: JSON (list of strings)
├── preference_score_summary: JSON (aggregated scores)
├── purchase_intent_score: Float (0-100, indexed)
├── last_interaction_at: DateTime
├── created_at: DateTime
└── updated_at: DateTime

KnowledgeDocument
├── id: UUID (PK)
├── document_type: Enum(FAQ, RETURN_POLICY, PAYMENT_POLICY, SHIPPING_POLICY, PRODUCT_GUIDE, SUPPORT_ARTICLE)
├── title: String
├── slug: String (unique, nullable)
├── source: String (default: internal)
├── content: Text (full document text)
├── metadata: JSON
├── is_active: Boolean
├── created_at: DateTime
└── updated_at: DateTime

KnowledgeChunk (RAG Support)
├── id: UUID (PK)
├── document_id: UUID (FK)
├── chunk_index: Int
├── content: Text (chunk text for RAG)
├── embedding_ref: String? (external embedding vector reference)
├── metadata: JSON
├── created_at: DateTime
└── [Constraint] unique(document, chunk_index)

ChatSession
├── id: UUID (PK)
├── user_id: UUID? (nullable for anonymous)
├── session_title: String?
├── created_at: DateTime
└── updated_at: DateTime

ChatMessage
├── id: UUID (PK)
├── session_id: UUID (FK)
├── role: Enum(USER, ASSISTANT)
├── content: Text
├── metadata: JSON (e.g., embeddings, context)
├── created_at: DateTime
└── updated_at: DateTime
```

#### Serializers

- `BehavioralEventSerializer`: event_type, user_id, product_id, price, metadata, etc.
- `BulkBehavioralEventSerializer`: `{events: [...]}`
- `UserPreferenceSummarySerializer`: brands, categories, price_ranges, keywords, scores
- `RecommendationSerializer`: Product recommendations with scores and reasoning
- `ChatSessionSerializer`: Session info with message count
- `ChatMessageSerializer`: User/assistant message with content
- `KnowledgeDocumentSerializer`: Document with title, type, content

#### Authentication

- **Public Event Endpoints:** Appears public but may have rate limiting
- **Internal Endpoints:** `X-Internal-Service-Key` header
- **User Endpoints:** JWT token
- **Admin Endpoints:** Admin role

#### Response Format

Same: `{success, message, data}`

#### Event Tracking Format

**From any service (POST /api/v1/ai/events/track/ or bulk):**

```json
{
  "event_type": "order_created",
  "user_id": "user-uuid",
  "session_id": "session-123",
  "product_id": "prod-uuid",
  "brand_name": "TechBrand",
  "category_name": "Electronics",
  "price_amount": "1500.00",
  "price_range": "PREMIUM",
  "source_service": "order_service",
  "occurred_at": "2026-04-11T10:30:00Z",
  "metadata": {
    "order_id": "order-uuid",
    "order_value": "3000.00"
  }
}
```

**Bulk Events (POST /api/v1/internal/ai/events/ or /api/v1/ai/events/bulk/):**

```json
{
  "events": [
    {...event1...},
    {...event2...},
    {...event3...}
  ]
}
```

#### Event Types Monitored

| Event | Service | Payload |
|-------|---------|---------|
| SEARCH | (future) | keyword, filter_category |
| PRODUCT_VIEW | (would be frontend) | product_id, category, price |
| PRODUCT_CLICK | (would be frontend) | product_id, variant_id |
| ADD_TO_CART | cart_service | product_id, quantity |
| REMOVE_FROM_CART | cart_service | product_id, quantity |
| CHECKOUT_STARTED | cart_service | item_count, subtotal |
| ORDER_CREATED | order_service | order_id, total_items, order_value, products[] |
| PAYMENT_SUCCESS | payment_service | order_id, payment_amount |
| CHAT_QUERY | ai_service | keyword, session_id |

#### Inter-Service Communication

**Called by:**
- Order Service: Post order_created event
- Payment Service: Post payment_success event
- Cart Service: Post add_to_cart, remove_from_cart, checkout_started events
- (Frontend would post: product_view, product_click, search events)

**Calls to:**
- None

---

## Integration Flow Analysis

### 1. Order Creation Flow (End-to-End)

```
Customer → Cart (add items) → Order Service (checkout)
                                    ↓
                        1. Cart Service: validate_cart()
                        2. Cart Service: build_checkout_payload()
                        3. Create Order: PENDING
                        4. Inventory: create_reservations()
                              ↓
                        5. Payment: create_payment()
                        6. Cart: mark_checked_out()
                        7. Return checkout info to customer
                              ↓
                        8. Payment: customer completes payment
                        9. Payment webhook: payment-callback
                              ↓
                        10. Order Service (internal): payment-success()
                              ↓
                        11. Inventory: confirm_reservations()
                        12. Update Order: CONFIRMED
                        13. Shipping: create_shipment()
                        14. AI: track event (order_created)
```

**Potential Mismatch:**
- Cart Service must return items in format matching OrderItem structure
- Cart checkout_payload fields must match Order Service expectation
- Inventory reservation response must be stored in `stock_reservation_refs`

### 2. Cart Checkout Payload → Order Schema

**Cart Checkout Response:**
```json
{
  "items": [
    {
      "product_id": "...",
      "variant_id": "...",
      "quantity": 2,
      "unit_price": "1500.00",
      "product_name": "Laptop Pro",
      "brand": "TechBrand",
      "category": "Electronics",
      "sku": "SKU123"
    }
  ],
  "subtotal": "3000.00",
  "currency": "USD"
}
```

**Order Service Must Convert To:**
```json
{
  "items": [
    {
      "product_id": "...",
      "variant_id": "...",
      "quantity": 2,
      "unit_price": 1500.00,
      "product_name_snapshot": "Laptop Pro",
      "brand_name_snapshot": "TechBrand",
      "category_name_snapshot": "Electronics",
      "sku": "SKU123"
    }
  ],
  "subtotal_amount": 3000.00,
  "currency": "USD"
}
```

**Issue:** Cart returns strings for prices (line_total, unit_price), Order expects Decimal

### 3. Stock Reservation → Order Confirmation

**Order Reserve Request:**
```json
{
  "order_id": "order-uuid",
  "user_id": "user-uuid",
  "items": [
    {"product_id": "...", "quantity": 2},
    {"product_id": "...", "quantity": 1}
  ]
}
```

**Inventory Response:**
```json
{
  "success": true,
  "data": {
    "reservations": [
      {"id": "res-1", "status": "ACTIVE", "expires_at": "..."},
      {"id": "res-2", "status": "ACTIVE", "expires_at": "..."}
    ]
  }
}
```

**Order Must Store:** Array of reservation IDs in `stock_reservation_refs` for later confirmation/release

### 4. Payment Async Callback → Order Confirmation

**Payment Success Callback to Order:**
```
POST /api/v1/internal/orders/{order_id}/payment-success/
{
  "payment_id": "payment-uuid",
  "payment_reference": "PAY-20260411-123456"
}
```

**Order Service Must:**
1. Confirm stock reservations via Inventory Service
2. Update order payment_status to COMPLETED
3. Update order status to CONFIRMED
4. Trigger shipment creation
5. Emit order_created event to AI Service

### 5. Shipment Status Updates → Order Tracking

**Shipping → Order Callback:**
```
POST /api/v1/internal/orders/{order_id}/shipment-status-updated/
{
  "shipment_id": "shipment-uuid",
  "status": "PICKED_UP",
  "location": "Distribution Center XYZ"
}
```

**Order Service Must:**
1. Update order fulfillment_status
2. Update shipment_id and shipment_reference
3. Possibly update status timeline

---

## Authentication Strategy Summary

| Service | Public Access | Customer Auth | Admin Auth | Internal Auth |
|---------|---------------|---------------|-----------|---------------|
| User | Register/Login only | JWT | JWT + Admin role | Internal Key |
| Product | Full CRUD public | No auth needed | JWT + Staff role | Internal Key |
| Inventory | No public | No auth needed | JWT + Admin role | Internal Key |
| Cart | No public | JWT token | No | Internal Key |
| Order | No public | JWT token | JWT + Admin role | Internal Key |
| Payment | Webhook public | JWT token | No | Internal Key |
| Shipping | List/Detail public | JWT token | No | Internal Key |
| AI | Track events public | JWT for preferences | JWT + Admin | Internal Key |

**Common Headers:**
- JWT: `Authorization: Bearer <jwt_token>`
- Internal: `X-Internal-Service-Key: <key>`
- User Context: `X-User-ID: <uuid>` (optional, from JWT)

---

## Identified Integration Mismatches & Risks

### ⚠️ CRITICAL ISSUES

#### 1. **Cart Price Serialization Mismatch**
- **Problem:** Cart serializer returns prices as strings, Order expects Decimal
- **Impact:** Order creation will fail or have precision issues
- **Location:** cart_service.presentation.serializers.CartItemSerializer
- **Fix:** Ensure cart returns prices as numbers in JSON, not strings

#### 2. **Missing Inventory Confirmation Error Handling**
- **Problem:** Order service must handle inventory confirmation failure but doesn't fail gracefully
- **Impact:** If inventory confirmation fails, order remains paid but stock not confirmed
- **Location:** order_service.infrastructure.clients.InventoryServiceClient.confirm_reservations()
- **Fix:** Implement compensating transaction (refund payment) on confirmation failure

#### 3. **Async Payment Callback Race Condition**
- **Problem:** Order doesn't lock during payment await, customer might cancel while payment processing
- **Impact:** Payment succeeds but order is cancelled, creating orphaned payment
- **Location:** order_service.presentation.api.OrderViewSet
- **Fix:** Implement order status lock (PROCESSING) during payment window

#### 4. **Missing Inventory Expiry Handling**
- **Problem:** Stock reservations expire (default 60 minutes), but no automatic cleanup or re-reservation
- **Impact:** Long checkout process → reserved items released → order fails mysteriously
- **Location:** inventory_service.infrastructure.models.StockReservationModel.expires_at
- **Fix:** Implement reservation renewal or extend timeout during checkout

---

### ⚠️ HIGH IMPACT ISSUES

#### 5. **Incomplete Event Tracking from Order Service**
- **Problem:** Order service doesn't emit events to AI service about order creation details
- **Impact:** AI profiles missing critical order signal data
- **Location:** order_service.infrastructure.clients (no AI client)
- **Fix:** Add event emission: order items, total, timeline

#### 6. **No Idempotency for Payment Webhooks**
- **Problem:** Webhook callback could fire multiple times, payment_success called twice
- **Impact:** Stock confirmed twice, order status corrupted
- **Location:** payment_service.presentation.views.PaymentWebhookViewSet
- **Fix:** Implement idempotency key in webhook handling

#### 7. **Shipping Address Validation Missing**
- **Problem:** Order accepts shipping_address but doesn't validate against user addresses
- **Impact:** Order placed to invalid/fake address, can't be shipped
- **Location:** order_service.presentation.serializers.CreateOrderFromCartSerializer
- **Fix:** Option 1: Validate against user_service addresses; Option 2: Allow submission but flag for verification

#### 8. **Payment Provider Metadata Not Standardized**
- **Problem:** Different providers (STRIPE vs VNPAY) return different webhook formats
- **Impact:** Payment service unable to parse certain providers
- **Location:** payment_service.infrastructure clients for each provider
- **Fix:** Normalize all provider responses to standard format

---

### ⚠️ MEDIUM IMPACT ISSUES

#### 9. **No Response Format Consistency Enforcement**
- **Problem:** Some endpoints return `{success, data}`, some return raw data or different structure
- **Impact:** Clients must handle multiple response formats
- **Recommendation:** Standardize all endpoints to use consistent envelope

#### 10. **Missing Cart Validation Before Checkout**
- **Problem:** Cart items marked UNAVAILABLE but still allowed in checkout
- **Impact:** Customer proceeds to payment for unavailable items
- **Location:** cart_service.presentation.api.CustomerCartViewSet.checkout_preview()
- **Fix:** Block checkout if any item marked UNAVAILABLE or OUT_OF_STOCK

#### 11. **Product Price Changes Not Reflected in Cart**
- **Problem:** Cart stores unit_price_snapshot but doesn't warn if current price differs
- **Impact:** Customer confusion about final order price
- **Location:** cart_service.infrastructure.models.CartItemModel
- **Fix:** Implement price validation in checkout to warn of changes

#### 12. **Incomplete Cancellation Cascade**
- **Problem:** Cancelling order doesn't automatically trigger shipment cancellation if shipped
- **Impact:** Orphaned shipments in system
- **Location:** order_service.presentation.api.OrderViewSet.cancel()
- **Fix:** Call shipping_service.cancel_shipment() if fulfillment_status >= SHIPPED

---

### ℹ️ LOWER PRIORITY ISSUES

#### 13. **No User Service Called During Order Creation**
- **Problem:** Order stored user info from JWT but doesn't validate user still exists/active
- **Impact:** Can create order for deleted user account
- **Location:** order_service.infrastructure.clients (no user client)
- **Fix:** Validate user_active from user_service before confirming order

#### 14. **Shipping Address Missing Ward Nullability Handling**
- **Problem:** Some addresses have ward field, some don't, but Order stores as required String
- **Impact:** Address display/return label issues for regions without wards
- **Location:** order_service.infrastructure.models.OrderModel
- **Fix:** Make shipping_ward nullable (already is)

#### 15. **AI Event Type Enums Not Comprehensive**
- **Problem:** BehavioralEvent only covers current flows, missing future events (returns, refunds, reviews)
- **Impact:** Can't extend event tracking without migration
- **Location:** ai_service.modules.ai.domain.value_objects.EventType
- **Fix:** Add extensible event type system or allow custom metadata

---

## Recommendations

### Immediate Actions (This Sprint)

1. **Add Type Validation Tests:** Test all service-to-service contracts with actual JSON payloads
2. **Implement Idempotency Keys:** Add to payment webhook and inventory endpoints
3. **Add Compensating Transactions:** Implement refund on failed inventory confirmation
4. **Extended Reservation Timeout:** Change default from 60 to 180 minutes during checkout

### Short Term (Next Sprint)

5. **Standardize Response Envelopes:** Ensure all endpoints use consistent `{success, message, data, errors}` format
6. **Add Request Tracing:** Implement correlation IDs across all service calls
7. **Add Event Emission:** Connect order_service to ai_service for comprehensive tracking
8. **Implement Webhook Signature Verification:** Validate payment provider webhooks cryptographically

### Medium Term (Roadmap)

9. **Add Service Mesh:** Implement retry policies, circuit breakers, observability (e.g., Istio/Linkerd)
10. **Upgrade to Event-Driven:** Replace HTTP callbacks with message bus (RabbitMQ/Kafka)
11. **Add SAGA Pattern:** Implement order creation as distributed transaction with compensation
12. **Add Contract Testing:** Use Pact or equivalent for continuous contract verification

---

## Response Format Standardization (Recommended)

All services should respond with:

```json
{
  "success": true|false,
  "message": "Human readable message",
  "data": {...}|null,
  "errors": {...}|null,
  "timestamp": "ISO-8601",
  "request_id": "correlation-id"
}
```

**HTTP Status Codes:**
- Success: 200, 201
- Client Error: 400 (validation), 401 (auth), 403 (forbidden), 404 (not found)
- Server Error: 500, 502, 503

---

## Conclusion

The TechShop microservices architecture has a well-structured API design with:

✓ **Strengths:**
- Consistent response envelope across most services
- Clear authentication separation (public/JWT/internal)
- Domain-driven design with proper bounded contexts
- Comprehensive inter-service client implementations

⚠️ **Weaknesses:**
- Lack of idempotency handling for async callbacks
- Missing compensating transactions for saga patterns
- Incomplete event tracking from order/payment services
- Type mismatches between service contracts
- No request-level tracing/correlation

The identified mismatches are mostly solvable with configuration/implementation fixes rather than architectural changes. Priority should be given to adding idempotency, error handling, and event tracking to ensure reliable order fulfillment flows.

---

**Report Generated:** April 11, 2026  
**Analysis Scope:** All 8 services, API contracts, data models, inter-service communication
