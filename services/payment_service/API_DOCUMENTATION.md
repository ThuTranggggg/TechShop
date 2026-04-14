# Payment Service API Documentation

## Base URL

```
http://localhost:8005/api/v1/
```

## Authentication

All endpoints require service-to-service authentication via header:

```
X-Service-Auth: <service-token>
```

## Response Format

All responses follow a standard format:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Response

```json
{
  "success": false,
  "data": null,
  "error": "Error message describing what went wrong",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## API Endpoints

### 1. Create Payment

**Endpoint**: `POST /payments/`

**Description**: Create a new payment for an order.

**Request Body**:
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "order_number": "ORD-001",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "amount": 99.99,
  "currency": "USD",
  "provider": "stripe",
  "method": "card",
  "description": "Order payment",
  "return_url": "https://example.com/return",
  "cancel_url": "https://example.com/cancel",
  "success_url": "https://example.com/success"
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| order_id | UUID | Yes | Unique order identifier |
| order_number | String | Yes | Human-readable order number |
| user_id | UUID | No | User making the payment |
| amount | Decimal | Yes | Payment amount (2 decimal places) |
| currency | String | Yes | ISO 4217 currency code (USD, EUR, etc.) |
| provider | String | Yes | Payment provider: `stripe`, `paypal`, `square` |
| method | String | Yes | Payment method: `card`, `digital_wallet`, `bank_transfer` |
| description | String | No | Payment description |
| return_url | String | No | URL to return after payment (provider dependent) |
| cancel_url | String | No | URL on payment cancellation |
| success_url | String | No | URL on payment success |

**Success Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "payment_reference": "pay_1234567890abcdef",
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "order_number": "ORD-001",
    "amount": 99.99,
    "currency": "USD",
    "status": "requires_action",
    "provider": "stripe",
    "method": "card",
    "checkout_url": "https://checkout.stripe.com/pay/...",
    "client_secret": null,
    "description": "Order payment",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "transactions": []
  }
}
```

**Error Cases**:
- `400 Bad Request` - Invalid input or existing active payment
- `422 Unprocessable Entity` - Validation error (amount format, currency, etc.)
- `500 Internal Server Error` - Provider communication failure

**Example**:
```bash
curl -X POST http://localhost:8005/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -H "X-Service-Auth: token" \
  -d '{
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "order_number": "ORD-001",
    "amount": 99.99,
    "currency": "USD",
    "provider": "stripe",
    "method": "card"
  }'
```

---

### 2. Get Payment Detail

**Endpoint**: `GET /payments/{payment_id}/`

**Description**: Get full details of a specific payment.

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| payment_id | UUID | path | Yes | Payment ID |

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "payment_reference": "pay_1234567890abcdef",
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 99.99,
    "currency": "USD",
    "status": "paid",
    "provider": "stripe",
    "method": "card",
    "checkout_url": null,
    "description": "Order payment",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:01:00Z",
    "transactions": [
      {
        "id": "txn_001",
        "type": "create",
        "status": "success",
        "amount": 99.99,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": "txn_002",
        "type": "callback",
        "status": "success",
        "amount": 99.99,
        "created_at": "2024-01-01T00:01:00Z"
      }
    ]
  }
}
```

**Error Cases**:
- `404 Not Found` - Payment not found
- `500 Internal Server Error` - Database error

---

### 3. Get Payment by Reference

**Endpoint**: `GET /payments/reference/{reference}/`

**Description**: Get payment details by payment reference.

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| reference | String | path | Yes | Payment reference (e.g., `pay_...`) |

**Success Response**:
Same as "Get Payment Detail"

**Error Cases**:
- `404 Not Found` - Payment not found

**Example**:
```bash
curl -X GET http://localhost:8005/api/v1/payments/reference/pay_1234567890abcdef/ \
  -H "X-Service-Auth: token"
```

---

### 4. Get Payment Status (Quick)

**Endpoint**: `GET /payments/{reference}/status/`

**Description**: Get quick payment status without full details.

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| reference | String | path | Yes | Payment reference |

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "payment_reference": "pay_1234567890abcdef",
    "status": "paid",
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 99.99,
    "currency": "USD",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:01:00Z"
  }
}
```

**Use Cases**:
- Quick status checks from frontend
- Polling for payment confirmation
- Lightweight status updates

---

### 5. Cancel Payment

**Endpoint**: `POST /payments/{reference}/cancel/`

**Description**: Cancel an active payment.

**Parameters**:
| Name | Type | In | Required |
|------|------|-----|----------|
| reference | String | path | Yes |

**Request Body** (optional):
```json
{
  "reason": "User requested cancellation"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "payment_reference": "pay_1234567890abcdef",
    "status": "cancelled",
    "cancelled_reason": "User requested cancellation",
    "cancelled_at": "2024-01-01T00:02:00Z"
  }
}
```

**Error Cases**:
- `400 Bad Request` - Already cancelled or in terminal state
- `404 Not Found` - Payment not found
- `500 Internal Server Error` - Provider cancellation failed

**Idempotent**: Cancelling already cancelled payment returns success.

---

### 6. Expire Payment

**Endpoint**: `POST /payments/{reference}/expire/`

**Description**: Manually expire a payment (usually called by expiry job).

**Parameters**:
| Name | Type | In | Required |
|------|------|-----|----------|
| reference | String | path | Yes |

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "Payment expired"
  }
}
```

**Use Cases**:
- Scheduled jobs expiring old payments
- Admin manual expiry
- Test environment cleanup

---

### 7. Handle Webhook Callback

**Endpoint**: `POST /webhooks/{provider}/`

**Description**: Receive payment provider callbacks/webhooks.

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| provider | String | path | Yes | Provider: `stripe`, `paypal`, `square` |

**Request Body**:
Varies by provider. Examples:

**Stripe**:
```json
{
  "id": "evt_1234567890",
  "object": "event",
  "api_version": "2023-10-16",
  "created": 1704110400,
  "data": {
    "object": {
      "id": "ch_1234567890abcdef",
      "object": "charge",
      "status": "succeeded"
    }
  },
  "type": "charge.succeeded"
}
```

**PayPal**:
```json
{
  "id": "WH-1234567890",
  "event_type": "PAYMENT.SALE.COMPLETED",
  "resource": {
    "parent_payment": "PAY-1234567890",
    "sale_id": "SALE-1234567890",
    "status": "completed"
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "message": "Webhook received"
  }
}
```

**Important Notes**:
- Always returns `200 OK` to signal receipt
- Idempotent - same webhook can be processed multiple times
- Verification: provider signature verified internally
- Async processing: callback handling is synchronous but retryable

**Provider-Specific Details**:

#### Stripe
- Event types handled: `charge.succeeded`, `charge.failed`
- Signature header: `Stripe-Signature`
- Documentation: https://stripe.com/docs/webhooks

#### PayPal
- Event types handled: `PAYMENT.SALE.COMPLETED`, `PAYMENT.SALE.DENIED`
- Documentation: https://developer.paypal.com/docs/api-basics/notifications/webhooks/

---

## Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input or business rule violation |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error, retry or contact support |

---

## Payment Status Values

| Status | Description | Possible Transitions |
|--------|-------------|-------------------|
| `created` | Payment entity created | → pending |
| `pending` | Awaiting provider response | → requires_action, failed |
| `requires_action` | User action needed (3D Secure, etc.) | → paid, failed, cancelled |
| `paid` | Payment successful | (terminal) |
| `failed` | Payment failed | (terminal) |
| `cancelled` | Payment cancelled by user/system | (terminal) |
| `expired` | Payment expired (timeout) | (terminal) |

---

## Provider Support Matrix

| Provider | Status | Methods | Currencies |
|----------|--------|---------|-----------|
| Stripe | ✓ | card, digital_wallet | USD, EUR, GBP, ... |
| PayPal | ✓ | digital_wallet, bank_transfer | USD, EUR, GBP, ... |
| Square | ✓ | card, digital_wallet | USD, CAD, AUD, ... |

---

## Rate Limiting

- No rate limiting currently implemented
- Planned: 100 requests/minute per service

---

## Webhook Security

### Stripe
Requests include `Stripe-Signature` header with timestamp and signature:
```
Stripe-Signature: t=1632755383,v1=5257...
```

### PayPal
Requests include `PAYPAL-TRANSMISSION-ID`, `PAYPAL-TRANSMISSION-TIME`, etc.

---

## Example Workflows

### Complete Payment Flow

```
1. Frontend creates order
2. Frontend → POST /api/v1/payments/
3. Server returns checkout URL
4. Frontend redirects to checkout URL (Stripe/PayPal hosted page)
5. User completes payment on provider site
6. Provider → POST /api/v1/webhooks/stripe/
7. Server processes callback, updates payment status to "paid"
8. Server → OrderService API: notify payment success
9. OrderService acknowledges and proceeds with fulfillment
```

### Polling Flow (Alternative)

```
1. Frontend creates order
2. Frontend → POST /api/v1/payments/
3. Server returns payment reference
4. Frontend polls GET /api/v1/payments/{reference}/status/
5. Frontend waits for status = "paid"
6. Frontend confirms order
```

### Error Recovery

```
1. Payment creation succeeds but provider call fails
2. System marks payment as "pending"
3. Scheduled job retries payment creation
4. Or: System waits for provider webhook callback
5. On callback, status updated to "paid" or "failed"
```

---

## Best Practices

### For Frontend Integration

1. **Always validate response structure** - Never assume fields exist
2. **Handle all error cases** - Implement proper error UI
3. **Use payment_reference for queries** - More stable than payment_id
4. **Implement timeout** - Polling should timeout after 5 minutes
5. **Verify provider status** - Don't trust system status alone for sensitive operations

### For Backend Integration

1. **Verify webhook signatures** - Critical for security
2. **Implement idempotency** - Handle duplicate webhook deliveries
3. **Use service-to-service auth** - Validate all requests
4. **Log payment events** - Useful for debugging but never log sensitive data
5. **Implement retry logic** - Provider callbacks are retryable

### For Monitoring

1. **Alert on webhook failures** - May indicate provider or network issues
2. **Monitor payment completion rate** - Track conversion funnel
3. **Alert on stuck payments** - Payments pending > 1 hour
4. **Monitor provider latency** - Slow provider calls affect UX
5. **Track failed transactions** - Analyze failure patterns

---

## Troubleshooting

### Common Issues

**Problem**: Payment stuck in "requires_action"
- **Cause**: User didn't complete 3D Secure or checkout
- **Solution**: Verify checkout URL was accessed, check provider dashboard

**Problem**: Webhook not received
- **Cause**: Provider delivery failure or webhook URL incorrect
- **Solution**: Check webhook URL in provider settings, verify firewall rules

**Problem**: Payment created but provider call failed
- **Cause**: Network timeout or provider API error
- **Solution**: Retry creation or wait for webhook callback

---

## Changelog

### v0.1.0 (Initial Release)
- Basic payment creation
- Provider callbacks
- Payment status tracking
- Support for Stripe, PayPal, Square

### Planned Features
- Partial refunds
- Recurring payments
- Multi-currency support enhancements
- SCA/3D Secure handling
- Fraud detection integration
