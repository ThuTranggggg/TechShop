# Payment Service Implementation Guide

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis (for caching/Celery)
- Docker & Docker Compose

### Setup Development Environment

1. **Clone and navigate**:
```bash
cd services/payment_service
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize database**:
```bash
python manage.py migrate
```

6. **Run development server**:
```bash
python manage.py runserver 0.0.0.0:8005
```

7. **Test health endpoint**:
```bash
curl http://localhost:8005/health/
```

### Docker Setup

```bash
docker-compose up -d

# Wait for services to start
sleep 10

# Initialize database
docker-compose exec payment_service python manage.py migrate

# Create superuser (optional)
docker-compose exec payment_service python manage.py createsuperuser
```

---

## Architecture Overview

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture.

Quick overview:
```
Presentation (Views) → Application (Services) → Domain (Business Logic) → Infrastructure (ORM)
```

---

## Development Workflow

### 1. Creating a New Use Case (Feature)

**Example**: Add refund functionality

#### Step 1: Define Domain Entity

Add to `modules/payment/domain/entities.py`:

```python
class Refund:
    def __init__(self, payment_id: UUID, amount: Money):
        self.payment_id = payment_id
        self.amount = amount
        self.status = RefundStatus.CREATED
```

#### Step 2: Create Repository Interface

Add to `modules/payment/domain/repositories.py`:

```python
class RefundRepository(ABC):
    @abstractmethod
    def save(self, refund: Refund) -> Refund: pass
    
    @abstractmethod
    def get_by_id(self, refund_id: UUID) -> Optional[Refund]: pass
```

#### Step 3: Implement Repository

Add to `modules/payment/infrastructure/repositories.py`:

```python
class RefundRepositoryImpl(RefundRepository):
    def save(self, refund: Refund) -> Refund:
        model = RefundModel.from_domain(refund)
        model.save()
        return model.to_domain()
```

#### Step 4: Create Application Service

Add to `modules/payment/application/services.py`:

```python
class RefundPaymentService:
    def __init__(self, payment_repo: Optional[PaymentRepository] = None):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()
    
    def execute(self, payment_id: str, amount: Decimal):
        # Implementation
        pass
```

#### Step 5: Create API View

Add to `modules/payment/presentation/views.py`:

```python
class PaymentViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def refund(self, request):
        # Implementation
        pass
```

#### Step 6: Register URL

Add to `modules/payment/urls.py`:

```python
# Automatically included in ViewSet routing
```

#### Step 7: Add Tests

Create `modules/payment/tests/test_refund_service.py`:

```python
class TestRefundService:
    def test_refund_success(self):
        # Test implementation
        pass
```

### 2. Common Development Tasks

#### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest modules/payment/tests/test_payment_services.py

# With coverage report
pytest --cov=modules.payment

# Watch mode (auto-run on file changes)
pytest-watch
```

#### Database Migrations

```bash
# Create migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

#### Running Linters

```bash
# Format code
black modules/

# Check formatting
pylint modules/

# Type checking
mypy modules/
```

#### Debugging

```bash
# Using print debugging
# Add to your code:
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")

# Check logs:
tail -f logs/payment_service.log

# Using Python debugger
import pdb; pdb.set_trace()
```

---

## Configuration

### Environment Variables

See `.env.example` for all available options:

```env
# Service
SERVICE_NAME=payment_service
SERVICE_PORT=8005
DEBUG=True

# Database
DB_NAME=payment_service
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Payment Providers
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Logging
LOG_LEVEL=INFO
```

### Settings

Django settings in `config/settings.py`:

```python
# Add custom settings
MY_CUSTOM_SETTING = os.getenv("MY_CUSTOM_SETTING", "default")
```

---

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
def test_create_payment_service():
    # Arrange
    service = CreatePaymentService()
    request = CreatePaymentRequestDTO(...)
    
    # Act
    success, error, payment = service.execute(request)
    
    # Assert
    assert success
    assert payment is not None
```

### Integration Tests

Test multiple components together:

```python
def test_create_and_query_payment():
    # Create via API
    # Query via repository
    # Verify consistency
```

### Test Fixtures

Reusable test data:

```python
@pytest.fixture
def sample_payment():
    return Payment(...)

def test_something(sample_payment):
    # Uses sample_payment fixture
```

### Mocking External Services

```python
from unittest.mock import patch, Mock

def test_with_mocked_provider():
    with patch("modules.payment.infrastructure.PaymentProvider") as mock:
        mock.create_payment.return_value = Mock(success=True)
        # Your test
```

---

## Code Organization

### Module Structure

```
modules/payment/
├── domain/              # Business logic
│   ├── entities.py
│   ├── services.py
│   ├── repositories.py
│   ├── value_objects.py
│   └── factories.py
├── application/         # Use cases
│   ├── services.py
│   ├── dtos.py
│   └── __init__.py
├── infrastructure/      # Persistence & integration
│   ├── repositories.py
│   ├── models.py
│   ├── providers.py
│   ├── clients.py
│   └── __init__.py
├── presentation/        # HTTP API
│   ├── views.py
│   └── __init__.py
├── tests/              # Test suite
│   ├── test_payment_services.py
│   ├── test_domain.py
│   └── conftest.py
├── urls.py
├── apps.py
└── __init__.py
```

### Import Guidelines

```python
# Good: specific imports
from modules.payment.domain import Payment, Money

# Avoid: wildcard imports
from modules.payment.domain import *

# Good: relative imports in same package
from .entities import Payment

# Avoid: circular imports
# Don't import from presentation in domain
```

---

## Common Patterns

### Service Implementation Pattern

```python
class MyService:
    def __init__(self, repo=None):
        self.repo = repo or RepositoryImpl()
    
    @transaction.atomic
    def execute(self, request_dto):
        try:
            # Validate
            if not request_dto.is_valid():
                return False, "Error", None
            
            # Business logic
            entity = self.repo.get(...)
            entity.do_something()
            
            # Persist
            self.repo.save(entity)
            
            # Return
            return True, None, entity_to_dto(entity)
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, "Error message", None
```

### DTO Pattern

```python
@dataclass
class RequestDTO:
    field1: str
    field2: int
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        if not self.field1:
            return False, "field1 is required"
        return True, None

def entity_to_dto(entity: Entity) -> ResponseDTO:
    return ResponseDTO(...)
```

### Repository Pattern

```python
class MyRepositoryImpl(MyRepository):
    def save(self, entity: Entity) -> Entity:
        model = MyModel.from_domain(entity)
        model.save()
        return model.to_domain()
    
    def get_by_id(self, id: UUID) -> Optional[Entity]:
        try:
            model = MyModel.objects.get(id=id)
            return model.to_domain()
        except MyModel.DoesNotExist:
            return None
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging

# In your code
logger = logging.getLogger(__name__)
logger.debug("Debug message")

# In settings.py
LOGGING = {
    'root': {
        'level': 'DEBUG',
    }
}
```

### Database Query Debugging

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    # Your code here
    pass

for query in queries:
    print(f"{query['time']}s: {query['sql']}")
```

### API Response Debugging

```python
# Use Django Debug Toolbar
pip install django-debug-toolbar

# Add to INSTALLED_APPS
"debug_toolbar"

# Check /api/docs/ for OpenAPI schema
```

---

## Performance Optimization

### Database Optimization

```python
# Use select_related for foreign keys
payments = Payment.objects.select_related('order')

# Use prefetch_related for reverse relations
payments = Payment.objects.prefetch_related('transactions')

# Add database indexes
class PaymentModel(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['payment_reference']),
        ]
```

### Caching

```python
from django.core.cache import cache

# Set cache
cache.set('payment_key', payment_obj, timeout=300)

# Get from cache
cached = cache.get('payment_key')

# Use cache_page decorator
from django.views.decorators.cache import cache_page

@cache_page(300)  # 5 minutes
def get_payment_status(request):
    pass
```

### Query Optimization

```python
# Use only() to limit fields
payments = Payment.objects.only('id', 'status')

# Use values() for specific columns
payments = Payment.objects.values('id', 'status')

# Batch operations
Payment.objects.bulk_create([payment1, payment2])
```

---

## Troubleshooting

### Common Issues

#### ImportError: No module named 'modules.payment'

**Solution**: Ensure `modules.payment` is in `INSTALLED_APPS` in `config/settings.py`

#### Database connection error

**Solution**: Check DATABASE settings in `.env`:
```bash
python manage.py shell
from django.db import connection
connection.ensure_connection()  # Will raise error if can't connect
```

#### Tests fail with Django setup

**Solution**: Use `pytest` with proper configuration:
```bash
pytest --ds=config.settings
```

#### Circular import error

**Solution**: Avoid importing from higher layers:
- Domain should not import Application/Presentation
- Application should not import Presentation

#### Slow database queries

**Solution**: Use Django Debug Toolbar:
```python
# settings.py
if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
```

---

## Deployment

### Pre-deployment Checklist

- [ ] All tests pass: `pytest`
- [ ] Code formatted: `black modules/`
- [ ] No linting errors: `pylint modules/`
- [ ] Migrations ready: `python manage.py makemigrations`
- [ ] Environment variables set
- [ ] Database backed up
- [ ] Health check working

### Build Docker Image

```bash
docker build -t payment-service:latest .
```

### Deploy to Kubernetes

See [DEPLOYMENT_AND_VERIFICATION_GUIDE.md](../DEPLOYMENT_AND_VERIFICATION_GUIDE.md)

---

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Payment Provider Docs](README.md#external-integrations)

---

## Getting Help

1. Check existing tests for examples
2. Review architecture documentation
3. Check payment provider documentation
4. Ask in team communication channel
5. Create an issue with:
   - What you're trying to do
   - Expected vs actual behavior
   - Relevant code/logs
   - Environment details
