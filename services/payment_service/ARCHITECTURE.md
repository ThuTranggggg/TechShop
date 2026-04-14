# Payment Service Architecture

## Overview

The Payment Service implements a Domain-Driven Design (DDD) architecture with clear separation of concerns across four layers:

1. **Domain Layer** - Business logic and rules
2. **Application Layer** - Use cases and orchestration
3. **Infrastructure Layer** - External integrations and persistence
4. **Presentation Layer** - HTTP API endpoints

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│           Presentation Layer (Views)                │
│    - PaymentViewSet (REST API endpoints)            │
│    - PaymentWebhookViewSet (Webhook handlers)       │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│       Application Layer (Services)                  │
│   - CreatePaymentService                            │
│   - GetPaymentDetailService                         │
│   - HandlePaymentCallbackService                    │
│   - CancelPaymentService                            │
│   - and more use cases...                           │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│       Domain Layer (Entities)                       │
│   - Payment (Aggregate Root)                        │
│   - PaymentTransaction                              │
│   - Money (Value Object)                            │
│   - PaymentStatus (Enumeration)                     │
│   - Domain Services                                 │
│   - Repositories (Interfaces)                       │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│    Infrastructure Layer (Implementations)          │
│   - PaymentRepositoryImpl                            │
│   - PaymentTransactionRepositoryImpl                 │
│   - PaymentProviderFactory                          │
│   - StripeProvider, PaypalProvider, etc.            │
│   - OrderServiceClient                              │
│   - Database Models                                 │
└─────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### Domain Layer (`modules/payment/domain/`)

**Purpose**: Contains business logic independent of frameworks and external concerns.

**Key Components**:
- `entities.py` - Payment aggregate root and related entities
- `value_objects.py` - Money, PaymentProviderReference, etc.
- `repositories.py` - Repository interfaces (contracts)
- `services.py` - Domain services (PaymentStateTransitionService)
- `factories.py` - Domain factories for creating entities

**Characteristics**:
- No dependencies on Django, external APIs, or databases
- Pure business logic and rules
- Testable without external infrastructure

### Application Layer (`modules/payment/application/`)

**Purpose**: Orchestrates domain logic to implement use cases.

**Key Components**:
- `services.py` - Use case services:
  - `CreatePaymentService` - Create payment for order
  - `HandlePaymentCallbackService` - Process provider callbacks
  - `CancelPaymentService` - Cancel payment
  - And more...
- `dtos.py` - Request/Response DTOs for data transfer

**Responsibilities**:
- Coordinate domain services and repositories
- Validate requests
- Handle transactions
- Return results as DTOs

### Infrastructure Layer (`modules/payment/infrastructure/`)

**Purpose**: Implements technical concerns and external integrations.

**Key Components**:
- `repositories.py` - Repository implementations using Django ORM
- `providers.py` - Payment provider factory and implementations
- `clients.py` - External service clients (OrderService, etc.)
- `models.py` - Django ORM models

**Technologies**:
- Django ORM for database persistence
- HTTP clients for external services
- Payment provider SDKs (Stripe, PayPal, etc.)

### Presentation Layer (`modules/payment/presentation/`)

**Purpose**: Exposes HTTP API endpoints.

**Key Components**:
- `views.py` - Django REST ViewSets:
  - `PaymentViewSet` - CRUD operations on payments
  - `PaymentWebhookViewSet` - Provider webhooks

**API Endpoints**:
- `POST /api/v1/payments/` - Create payment
- `GET /api/v1/payments/{payment_id}/` - Get payment detail
- `GET /api/v1/payments/reference/{reference}/` - Get by reference
- `POST /api/v1/payments/{reference}/cancel/` - Cancel payment
- `POST /api/v1/webhooks/{provider}/` - Handle webhooks

## Data Flow

### Creating a Payment

```
1. Client                 → POST /api/v1/payments/
2. PaymentViewSet         → validate request → CreatePaymentService.execute()
3. CreatePaymentService   → create Payment entity → PaymentRepository.save()
4. PaymentRepository      → create PaymentModel → save to database
5. Payment Entity         → call payment provider → create charge
6. Provider               → return checkout URL
7. Application            → return PaymentDetailDTO
8. API                    → return 201 Created
```

### Handling Payment Callback

```
1. Provider               → POST /api/v1/webhooks/stripe/
2. WebhookViewSet         → parse payload → HandlePaymentCallbackService.execute()
3. Service                → find Payment → parse callback → update status
4. PaymentRepository      → update Payment in database
5. Service                → notify OrderService of success/failure
6. OrderService           → acknowledge and process payment
```

## State Machine

Payment states and transitions:

```
                        ┌──────────────┐
                        │   CREATED    │
                        └──────┬───────┘
                               │
                    ┌──PENDING──┼──REQUIRES_ACTION──┐
                    │           ▼           ▼       │
                    │      ┌─────────────────────┐ │
                    │      │ REQUIRES_ACTION     │ │
                    │      │ (user action needed)│ │
                    │      └──────┬──────────────┘ │
                    │             │                │
                    ▼             ▼                ▼
            ┌───────────────────────────────────────────┐
            │           PAID (SUCCESS)                  │
            └─────────────────────────────────────────────┘
                    │
                    │ (on failure/cancellation)
                    ▼
            ┌───────────────────────────────────────────┐
            │    FAILED / CANCELLED / EXPIRED           │
            └─────────────────────────────────────────────┘
```

## Key Concepts

### Domain Entities

#### Payment (Aggregate Root)
- Represents a payment transaction
- Manages state transitions
- Contains transactions list
- Tracks status and timestamps
- Immutable once created (except status transitions)

#### PaymentTransaction
- Records each operation (create, success, failure, callback)
- Stores provider response data
- Used for audit trail and retries

### Value Objects

#### Money
- Amount + Currency pair
- Immutable
- Ensures type safety and precision

#### PaymentProviderReference
- Links payment to provider's system
- Contains provider ID and reference

### Repositories

Repositories follow the Repository Pattern:
- Abstract persistence details
- Provide domain-focused queries
- Return domain entities, not database models

### Domain Services

#### PaymentStateTransitionService
- Validates state transitions
- Enforces business rules
- Handles state-specific logic

#### PaymentFactory
- Creates Payment entities with validation
- Ensures consistent creation logic

## Error Handling

### Validation Errors
- Input validation in DTOs
- Domain validation in services
- Clear error messages returned

### Transaction Safety
- Database transactions for atomic operations
- Idempotent operations where possible
- Failed operations don't corrupt state

### Retry Logic
- Service callbacks are retried by providers
- Payment status queries can refresh state
- Webhook delivery is idempotent

## Testing Strategy

### Unit Tests
- Test domain entities and services in isolation
- Mock repositories and external dependencies
- Test state transitions and business rules

### Integration Tests
- Test full use case flows
- Use test database
- Mock external providers

### Fixture Patterns
- Use factory fixtures for complex objects
- Mock external dependencies
- Use temporary test data

## Performance Considerations

- Database indexes on frequently queried fields:
  - `order_id`
  - `payment_reference`
  - `status`
  - `created_at`

- Caching:
  - Payment status queries can use short-lived cache
  - Provider reference mapping cached temporarily

- Async operations:
  - Provider callbacks processed synchronously
  - OrderService notifications could be async

## Security Considerations

- Payment data is never logged
- Provider tokens stored securely
- API calls authenticated via service auth
- Webhooks verified with provider signatures
- PCI compliance: sensitive card data not stored

## Extension Points

The architecture supports easy extension for:

1. **New Payment Providers**
   - Implement PaymentProvider interface
   - Register in PaymentProviderFactory
   - Add provider-specific handling in callbacks

2. **New Payment Methods**
   - Add to PaymentMethod enum
   - Update validation logic
   - Provider handles method-specific logic

3. **New Use Cases**
   - Create new Service class in application layer
   - Implement business logic using domain entities
   - Register endpoint in views

4. **Additional Notifications**
   - Extend HandlePaymentCallbackService
   - Add notification channels (SMS, email, etc.)

## Deployment

The service uses:
- Django WSGI for production
- PostgreSQL for persistence
- Redis for caching and async tasks
- Docker for containerization
- Kubernetes for orchestration

See [DEPLOYMENT_AND_VERIFICATION_GUIDE.md](../DEPLOYMENT_AND_VERIFICATION_GUIDE.md) for details.
