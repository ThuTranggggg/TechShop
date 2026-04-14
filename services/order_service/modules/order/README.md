# Order Service

**Order Service** là bounded context chuyên trách quản lý đơn hàng của toàn hệ thống e-commerce.

## Mục Đích & Vai Trò

Order Service là trái tim của checkout flow. Nó:

- Tạo đơn hàng từ cart một cách an toàn
- Quản lý lifecycle của đơn hàng theo state machine
- Điều phối stock reservation qua Inventory Service
- Điều phối payment qua Payment Service
- Điều phối shipment qua Shipping Service
- Lưu snapshot đầy đủ order tại thời điểm đặt hàng
- Cung cấp order history & detail cho end-user và admin

**Điểm quan trọng:**
- Order KHÔNG sở hữu Product domain
- Order KHÔNG sở hữu Inventory domain
- Order KHÔNG xử lý payment logic chi tiết
- Order KHÔNG xử lý shipment logistics chi tiết
- Order chỉ snapshot & orchestrate qua các service khác

## Kiến Trúc & DDD

Order Service được xây dựng theo nguyên lý **Domain-Driven Design**:

```
modules/order/
├── domain/               # Business logic & rules
│   ├── entities.py       # Order, OrderItem aggregates
│   ├── enums.py          # OrderStatus, PaymentStatus, etc.
│   ├── value_objects.py  # Money, OrderNumber, AddressSnapshot, etc.
│   ├── repositories.py   # Repository interfaces
│   ├── services.py       # Domain services (state machine, validation, calculation)
│   └── __init__.py
├── application/          # Use cases & orchestration
│   ├── dtos.py          # Data transfer objects
│   ├── services.py      # Application services (GetOrderDetail, CreateOrderFromCart, etc.)
│   └── __init__.py
├── infrastructure/       # ORM, external clients, persistence
│   ├── models.py        # Django ORM models
│   ├── repositories.py  # Repository implementations
│   ├── clients.py       # Inter-service HTTP clients
│   ├── migrations/      # Database migrations
│   └── __init__.py
├── presentation/         # API views & serializers
│   ├── api.py           # DRF viewsets
│   ├── serializers.py   # Request/response serialization
│   ├── permissions.py   # Authorization
│   ├── urls.py          # URL routing
│   └── __init__.py
├── management/           # Management commands
│   └── commands/
│       └── seed_orders.py
├── tests/               # Test suite
│   ├── test_models.py
│   ├── test_domain.py
│   ├── test_application.py
│   └── test_api.py
├── admin.py             # Django admin
├── apps.py              # Django app config
└── __init__.py
```

## Order State Machine

```
                    ┌──────────
                    v          |
              concurrent tracking:
              ├─ order_status
              ├─ payment_status
              └─ fulfillment_status
              
pending
    ↓
awaiting_payment  ←─── thời điểm stock reservation
    ├─→ paid       ←─── payment success
    └─→ payment_failed  ← payment failure
    
paid
    ↓
processing  ←─── stock confirmed, preparing shipment
    ↓
shipping    ←─── shipment created
    ↓
delivered   ←─── delivery confirmed
    ↓
completed   ←─── final state

cancel policy:
  - PENDING / AWAITING_PAYMENT / PAYMENT_FAILED → CANCELLED (ok)
  - PAID / PROCESSING → CANCELLED (có điều kiện)
  - SHIPPING / DELIVERED / COMPLETED → CANCELLED (không được)
```

Các status riêng biệt:

**order_status**: Main lifecycle
- `pending`: Vừa tạo, chưa xong orchestration
- `awaiting_payment`: Stock reserved, chờ payment
- `paid`: Payment thành công
- `processing`: Xử lý & chuẩn bị shipment
- `shipping`: Đang vận chuyển
- `delivered`: Giao thành công
- `completed`: Hoàn tất toàn bộ
- `payment_failed`: Payment fail
- `cancelled`: Order bị hủy

**payment_status**: Payment lifecycle
- `unpaid`: Chưa thanh toán
- `pending`: Payment đang xử lý
- `authorized`: Payment được phép (nhưng chưa capture)
- `paid`: Thanh toán thành công
- `failed`: Thanh toán thất bại
- `refunded`: Hoàn lại toàn bộ
- `partially_refunded`: Hoàn lại một phần

**fulfillment_status**: Shipment lifecycle
- `unfulfilled`: Chưa có shipment
- `preparing`: Đang chuẩn bị
- `shipped`: Đang vận chuyển
- `delivered`: Giao thành công
- `returned`: Khách hàng trả lại
- `cancelled`: Fulfillment bị hủy

## Dữ Liệu & Domain Models

### Order (Aggregate Root)

```python
Order(
    id: UUID                                    # System ID
    order_number: OrderNumber                   # ORD-20260411-000001
    user_id: UUID                               # Customer (from user_service)
    cart_id: UUID                               # Source cart (reference only)
    
    # Status
    status: OrderStatus                         # Main lifecycle
    payment_status: PaymentStatus               # Payment tracking
    fulfillment_status: FulfillmentStatus       # Shipment tracking
    currency: Currency                          # VND, USD, EUR
    
    # Pricing
    subtotal_amount: Decimal
    shipping_fee_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total_amount: Decimal
    
    # Quantities
    total_quantity: int
    item_count: int
    
    # Snapshot (at time of order)
    customer_name_snapshot: str
    customer_email_snapshot: str
    customer_phone_snapshot: str
    
    # Shipping address snapshot
    receiver_name: str
    receiver_phone: str
    shipping_line1: str
    shipping_line2: str
    shipping_ward: str
    shipping_district: str
    shipping_city: str
    shipping_country: str
    shipping_postal_code: str
    
    # References to external services
    payment_id: UUID | None
    payment_reference: str | None
    shipment_id: UUID | None
    shipment_reference: str | None
    stock_reservation_refs: List[Dict]
    
    # Relationship
    items: List[OrderItem]                      # Snapshot items
    
    # Milestones
    placed_at: datetime | None
    paid_at: datetime | None
    cancelled_at: datetime | None
    completed_at: datetime | None
    
    # Metadata
    notes: str
    created_at: datetime
    updated_at: datetime
)
```

### OrderItem

```python
OrderItem(
    id: UUID
    order_id: UUID                              # FK to Order
    product_reference: ProductReference         # (product_id, variant_id, sku)
    product_snapshot: ProductSnapshot           # All product info at purchase time
    
    quantity: int
    unit_price: Money
    currency: Currency
    
    # Product snapshot fields (immutable)
    product_name_snapshot: str
    product_slug_snapshot: str
    variant_name_snapshot: str | None
    brand_name_snapshot: str | None
    category_name_snapshot: str | None
    thumbnail_url_snapshot: str | None
    attributes_snapshot: Dict[str, Any]
    
    created_at: datetime
    updated_at: datetime
)
```

### OrderStatusHistory

```python
OrderStatusHistory(
    id: UUID
    order_id: UUID                              # FK to Order
    from_status: str | None                     # Previous status (null = initial)
    to_status: str                              # New status
    note: str                                   # Why changed
    changed_by: UUID | None                     # Who changed (null = system)
    metadata: Dict[str, Any]                    # Additional info
    created_at: datetime
)
```

## API Endpoints

### Public/Customer API

```
GET    /api/v1/orders/
       List user's orders (paginated)
       Headers: X-User-ID
       Response: OrderListItemDTO[]

GET    /api/v1/orders/{id}/
       Get order detail
       Headers: X-User-ID
       Response: OrderDetailDTO
       
POST   /api/v1/orders/from-cart/
       Create order from active cart
       Headers: X-User-ID
       Body: {
           "cart_id": "...",
           "shipping_address": {
               "receiver_name": "...",
               "receiver_phone": "...",
               "line1": "...",
               "district": "...",
               "city": "...",
               "country": "Vietnam"
           },
           "notes": "..." (optional)
       }
       Response: OrderDetailDTO (201 Created)

POST   /api/v1/orders/{id}/cancel/
       Cancel order
       Headers: X-User-ID
       Body: { "reason": "..." }
       Response: OrderDetailDTO
       
GET    /api/v1/orders/{id}/timeline/
       Get order status timeline
       Headers: X-User-ID
       Response: OrderTimelineDTO
       
GET    /api/v1/orders/{id}/status/
       Get current status
       Headers: X-User-ID
       Response: { status, payment_status, fulfillment_status }
```

### Internal API (Service-to-Service)

```
POST   /api/v1/internal/orders/create-from-cart/
       Create order (internal)
       Headers: X-Internal-Service-Key
       
GET    /api/v1/internal/orders/{id}/
       Get order (internal)
       Headers: X-Internal-Service-Key
       
POST   /api/v1/internal/orders/{id}/payment-success/
       Record payment success
       Headers: X-Internal-Service-Key
       Body: { "payment_id": "..." }
       Called by: payment_service
       
POST   /api/v1/internal/orders/{id}/payment-failed/
       Record payment failure
       Headers: X-Internal-Service-Key
       Body: { "reason": "..." }
       Called by: payment_service
       
POST   /api/v1/internal/orders/{id}/shipment-created/
       Record shipment creation
       Headers: X-Internal-Service-Key
       Called by: shipping_service (future)
```

### Admin API (future)

```
GET    /api/v1/admin/orders/
       List all orders
       Headers: X-User-Role: admin
       
PATCH  /api/v1/admin/orders/{id}/
       Update order
       
POST   /api/v1/admin/orders/{id}/mark-processing/
POST   /api/v1/admin/orders/{id}/mark-shipping/
POST   /api/v1/admin/orders/{id}/mark-delivered/
POST   /api/v1/admin/orders/{id}/complete/
       Force state transitions (admin only)
```

## Inter-Service Integration

### Cart Service Client

```python
# Get & validate cart
checkout_payload = cart_client.build_checkout_payload(cart_id, user_id)

# Mark cart as checked out after order creation
cart_client.mark_cart_checked_out(cart_id)
```

### Inventory Service Client

```python
# Reserve stock
reservation_ids = inventory_client.create_reservations(
    items=[
        {"product_id": "...", "quantity": 5},
        ...
    ],
    order_id=order_id,
    user_id=user_id,
)

# Confirm reservation after payment success
inventory_client.confirm_reservations(reservation_ids, order_id)

# Release reservation if payment fails or order cancelled
inventory_client.release_reservations(reservation_ids, order_id, reason="Payment failed")
```

### Payment Service Client

```python
# Create payment request
payment_info = payment_client.create_payment(
    order_id=order_id,
    user_id=user_id,
    amount=Decimal("500000"),
    currency="VND",
    order_number="ORD-20260411-000001",
    metadata={...}
)
# Returns: { payment_id, payment_reference, ... }

# Get payment status
status = payment_client.get_payment_status(payment_id)
```

### Shipping Service Client (prepared)

```python
# Create shipment after order paid
shipment_info = shipping_client.create_shipment(
    order_id=order_id,
    order_number=order_number,
    items=[...],
    shipping_address={...},
)

# Get shipment status
status = shipping_client.get_shipment_status(shipment_id)
```

## Order Creation Flow

```
┌─────────────────────────────────────────────────────┐
│ User có active cart hợp lệ                          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ POST /orders/from-cart/                             │
│ - Validate cart (via cart_service)                  │
│ - Build checkout payload                           │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Create Order domain object                          │
│ - Generate order_number                            │
│ - Snapshot customer & address                      │
│ - Build OrderItem snapshots                        │
│ - Calculate totals                                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Reserve stock (via inventory_service)              │
│ ❌ If fail → Abort order creation                   │
│ ✓ If ok → Get reservation_ids                      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Create payment request (via payment_service)       │
│ ❌ If fail → Rollback & abort                       │
│ ✓ If ok → Get payment_id & payment_reference       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Save Order + OrderItems to database                │
│ - status = AWAITING_PAYMENT                        │
│ - payment_status = PENDING                         │
│ - stock_reservation_refs = [...]                   │
│ - payment_reference = ...                          │
│ - Record in OrderStatusHistory                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Mark cart as checked_out (via cart_service)        │
│ (Soft failure - not critical)                      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ Return OrderDetailDTO + payment info to user       │
│ (User proceeds to payment)                          │
└──────────────────────────────────────────────────────┘
```

## Payment Success Flow

```
payment_service → POST /internal/orders/{id}/payment-success/
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Load Order from database             │
      │ Validate status = AWAITING_PAYMENT   │
      └──────────────────┬───────────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Confirm stock reservations           │
      │ (via inventory_service)              │
      │ ❌ If fail → Log warning, continue  │
      └──────────────────┬───────────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Update Order:                        │
      │ - status = PAID                      │
      │ - payment_status = PAID              │
      │ - paid_at = now()                    │
      │ - Record in OrderStatusHistory       │
      └──────────────────┬───────────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Return updated OrderDetailDTO        │
      │ (Order ready for processing)         │
      └──────────────────────────────────────┘
```

## Payment Failure Flow

```
payment_service → POST /internal/orders/{id}/payment-failed/
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Release stock reservations           │
      │ (via inventory_service)              │
      │ Reason: "Payment failed"             │
      │ ❌ If fail → Log warning, continue  │
      └──────────────────┬───────────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Update Order:                        │
      │ - status = PAYMENT_FAILED            │
      │ - payment_status = FAILED            │
      │ - Record in OrderStatusHistory       │
      └──────────────────┬───────────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ Return updated OrderDetailDTO        │
      │ (Order failed, user can retry)       │
      └──────────────────────────────────────┘
```

## Cancel Order Flow

```
POST /api/v1/orders/{id}/cancel/
        │
        ▼
┌─────────────────────────────────────────┐
│ Load Order, verify ownership            │
│ Validate cancellation allowed:          │
│ - Cannot cancel SHIPPED/DELIVERED/...   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ If reservation_refs exist:              │
│ Release them (via inventory_service)    │
│ Reason: "Order cancelled by user"       │
│ (Soft failure - continue anyway)        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Update Order:                           │
│ - status = CANCELLED                    │
│ - cancelled_at = now()                  │
│ - Record in OrderStatusHistory          │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Return OrderDetailDTO                   │
└─────────────────────────────────────────┘
```

## Business Rules

### Tạo Order

- Order chỉ được tạo từ valid cart
- Cart phải có ít nhất 1 item
- Customer info (name, email) bắt buộc
- Shipping address bắt buộc đầy đủ
- Stock phải được reserve thành công trước
- Payment phải được tạo thành công
- Chỉ 1 cart được checkout thành 1 order

### Snapshot Strategy

**Tại sao snapshot?**

Order record không nên phụ thuộc runtime vào product_service để hiển thị lịch sử. Nếu user xem order from 1 năm trước, nhưng product đã bị xóa, order history không nên bị hỏng.

**Snapshot được lưu:**

- Product name, slug, brand, category, variant
- Price tại thời điểm mua
- Customer name, email (từ checkout payload)
- Shipping address (từ checkout request)

**Không snapshot:**

- Không cần copy toàn bộ product catalog
- Reference chỉ lưu product_id (không cần product ID được)

### Inventory Integration

- Order phải reserve stock ngay khi tạo
- Reservation được hold tới khi payment success hoặc fail
- Payment success → confirm reservation
- Payment fail → release reservation
- Order cancel → release reservation
- Nếu reserve fail → order creation fail

### Payment Integration

- Payment phải được tạo ngay sau order creation
- Payment callback phải cập nhật order state
- Idempotent: payment callback 2 lần không duplicate
- Internal key guard: chỉ payment_service có thể gọi payment callbacks

## Setup & Running

### Requirements

- Python 3.9+
- Django 5.1+
- PostgreSQL
- (Optional) Redis

### Environment Variables

```bash
# .env
DEBUG=true
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1,order_service

DB_NAME=order_service
DB_USER=order_service
DB_PASSWORD=order_service_password
DB_HOST=order_service_db
DB_PORT=5432

SERVICE_PORT=8004
SERVICE_NAME=order_service

# Inter-service URLs
CART_SERVICE_URL=http://cart_service:8003
INVENTORY_SERVICE_URL=http://inventory_service:8007
PAYMENT_SERVICE_URL=http://payment_service:8005
SHIPPING_SERVICE_URL=http://shipping_service:8008

# Auth
INTERNAL_SERVICE_KEY=your-secret-key

CORS_ALLOW_ALL_ORIGINS=true
UPSTREAM_TIMEOUT=5
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Seed demo data
python manage.py seed_orders --count=10
```

### Running Locally

```bash
# Development server
python manage.py runserver 0.0.0.0:8004

# With gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8004

# Check health
curl http://localhost:8004/health/
curl http://localhost:8004/api/v1/health/

# View API docs
curl http://localhost:8004/api/docs/
```

### Docker

```bash
docker build -t order_service .
docker run -p 8004:8004 --env-file .env order_service
```

## Testing

### Run All Tests

```bash
python manage.py test modules.order.tests --verbosity=2
```

### Run Specific Test Class

```bash
python manage.py test modules.order.tests.test_domain.OrderEntityTests
python manage.py test modules.order.tests.test_application.CreateOrderFromCartServiceTests
python manage.py test modules.order.tests.test_api.OrderViewSetTests
```

### Test Coverage

```bash
coverage run --source='modules.order' manage.py test modules.order.tests
coverage report
```

## API Documentation

### OpenAPI/Swagger

Once running, visit:
```
http://localhost:8004/api/docs/
```

Or get raw schema:
```
curl http://localhost:8004/api/schema/
```

## Admin Panel

- URL: `http://localhost:8004/admin/`
- Models: Order, OrderItem, OrderStatusHistory
- Filters: status, payment_status, fulfillment_status, created_at
- Search: order_number, user_id, email, payment_reference

## Limitations & Future Improvements

### Current Limitations

- ✗ No refund engine (placeholder only)
- ✗ No return/RMA workflow
- ✗ No split shipment support
- ✗ No partial payment
- ✗ No coupon/discount engine
- ✗ Tax engine minimal
- ✗ Async event system basic (synchronous for now)
- ✗ No saga orchestration (simple orchestration only)
- ✗ No accounting/invoicing integration

### Future Improvements

1. **Refund Engine**
   - Partial/full refunds with inventory adjustment
   - Refund state machine tracking

2. **Return & RMA**
   - Return request workflow
   - Refund authorization
   - Returned item processing

3. **Split Orders**
   - When inventory split across multiple warehouses
   - Multiple shipments per order

4. **Advanced Orchestration**
   - Saga pattern for distributed transactions
   - Event-driven async processing
   - Compensation logic on failure

5. **Coupon & Tax Engine**
   - Coupon application & validation
   - Dynamic tax calculation
   - Discount tiers

6. **Accounting Integration**
   - Invoice generation
   - Financial reporting
   - Ledger entries

7. **Analytics & Metrics**
   - Order funnel analysis
   - Cancellation rate tracking
   - Revenue reporting

## Troubleshooting

### Order Creation Fails

**Cause: Cart Service Unavailable**
```
Solution: Ensure CART_SERVICE_URL in .env is correct
          Check cart_service is running
          Check network connectivity
```

**Cause: Inventory Reserve Failed**
```
Solution: Ensure INVENTORY_SERVICE_URL is correct
          Check inventory service is running
          Verify stock is available
```

**Cause: Invalid Cart Payload**
```
Solution: Validate checkout payload structure
          Ensure cart has supported items
          Check totals calculation
```

### Payment Callback Not Working

**Cause: Internal Key Mismatch**
```
Solution: Verify INTERNAL_SERVICE_KEY matches across services
          Check header: X-Internal-Service-Key
```

**Cause: Order Not Found**
```
Solution: Ensure order_id is correct UUID
          Verify order exists in database
```

### Migration Issues

```bash
# Show migration status
python manage.py showmigrations modules.order

# Roll back migration
python manage.py migrate modules.order 0000_previous

# Create new migration
python manage.py makemigrations modules.order
```

## Support & Questions

- Check README in order_service root
- Review API docs: `/api/docs/`
- Check logs in `logs/` directory
- Consult monorepo README for system-wide setup

## Related Services

- [Cart Service](../cart_service/README.md) - Shopping cart management
- [Product Service](../product_service/README.md) - Product catalog
- [Inventory Service](../inventory_service/README.md) - Stock management
- [Payment Service](../payment_service/README.md) - Payment processing
- [Shipping Service](../shipping_service/README.md) - Shipment management
- [User Service](../user_service/README.md) - Customer management

## License

Same as monorepo license.
