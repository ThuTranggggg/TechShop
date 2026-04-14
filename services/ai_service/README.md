# AI Service - Production-Ready Implementation

Comprehensive AI/Recommendation service for TechShop e-commerce microservices. Provides behavioral tracking, personalized recommendations, graph-based insights, and RAG-powered chat.

## Quick Links

- [Service Capabilities](#capabilities)
- [Architecture Overview](#architecture)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Examples](#examples)

## Capabilities

### 1. Behavioral Tracking (`BehavioralModel`)
- Track 9 event types: search, product_view, product_click, add_to_cart, remove_from_cart, checkout_started, order_created, payment_success, chat_query
- Automatic price range normalization (6 Vietnamese market buckets)
- Batch event ingestion (up to 1000/request)
- Session tracking and metadata support

### 2. User Preference Profiling (`UserPreferenceProfileModel`)
- Auto-built from behavioral events
- Captures: brand preferences, category preferences, price range preferences
- Purchase intent scoring (0-100)
- Recent keyword tracking (last 20 searches)

### 3. Personalized Recommendations
- Score-based ranking (0-100)
- Multi-attribute matching: brand + category + price
- Reason codes for transparency: preferred_brand, preferred_price_range, etc.
- Anonymous user fallback strategy
- Real product context integration ready

### 4. RAG Chat Engine
- Intent classification: product_search, order_status, shipment_status, policy_question, payment_status, general_support
- Knowledge base: FAQs, policies, guides, articles
- Keyword-based retrieval (vector search ready)
- Mock LLM provider (no hallucinations) + real provider abstraction
- Multi-turn session management

### 5. Graph Intelligence (Neo4j Ready)
- Mock implementation with full interface
- Node types: User, Product, Brand, Category, PriceRange
- Relationship types: VIEWED, CLICKED, PREFERS_BRAND, etc.
- Placeholder for advanced graph queries

## Architecture

```
modules/ai/
├── domain/                    # DDD Domain Layer
│   ├── entities.py           # BehavioralEvent, UserPreferenceProfile, etc
│   ├── value_objects.py      # EventType, PriceRange, ChatIntent, etc
│   ├── repositories.py       # Repository interfaces (contracts)
│   └── services.py           # Domain service interfaces
│
├── application/              # DDD Application Layer
│   └── services.py          # Use cases: Track, Recommend, Chat, etc
│
├── infrastructure/          # DDD Infrastructure Layer
│   ├── models.py            # Django ORM models
│   ├── repositories.py      # Repository implementations
│   ├── providers.py         # LLM provider abstraction + Mock
│   └── domain_services.py   # Domain service implementations
│
├── presentation/            # DDD Presentation Layer
│   ├── views.py            # API endpoints
│   ├── serializers.py      # Request/response validation
│   ├── urls.py             # URL routing
│   └── permissions.py      # Authorization (TBD)
│
├── admin.py                 # Django admin configuration
├── apps.py                  # Django app configuration
├── migrations/              # Database migrations
└── management/commands/     # Management commands
    └── seed_ai_data.py      # Seed demo data

common/                       # Shared utilities
├── responses.py             # Standard response format
├── exceptions.py            # Custom exceptions
├── health.py               # Health check endpoints
└── logging.py              # Structured logging
```

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Optional: Redis 7+, Neo4j 5+

### Installation

```bash
# 1. Clone and navigate to service
cd services/ai_service

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env (copy from .env.example and customize)
cp .env.example .env

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (optional)
python manage.py createsuperuser

# 7. Seed demo data
python manage.py seed_ai_data --users 5 --events-per-user 100

# 8. Start server
python manage.py runserver 0.0.0.0:8008
```

### Verify Installation

```bash
# Check health
curl http://localhost:8008/health/

# View API docs
open http://localhost:8008/api/docs/

# View admin
open http://localhost:8008/admin/
```

## API Documentation

### Event Tracking

**Track Single Event**
```bash
curl -X POST http://localhost:8008/api/v1/ai/events/track/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "product_click",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "550e8400-e29b-41d4-a716-446655440001",
    "brand_name": "Samsung",
    "category_name": "Smartphone",
    "price_amount": 8990000,
    "source_service": "product_detail"
  }'
```

**Bulk Track Events**
```bash
curl -X POST http://localhost:8008/api/v1/ai/events/bulk/ \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_type": "search", "keyword": "samsung"},
      {"event_type": "product_view", "product_id": "..."}
    ]
  }'
```

### Recommendations

**Score Products**
```bash
curl -X POST http://localhost:8008/api/v1/ai/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"id": "...", "name": "Samsung Galaxy S24", "brand": "Samsung", "category": "Smartphone", "price": 20000000},
      {"id": "...", "name": "iPhone 15", "brand": "Apple", "category": "Smartphone", "price": 25000000}
    ],
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "limit": 10
  }'
```

Response returns products sorted by score with reason_codes like `preferred_brand`, `preferred_price_range`.

### Chat

**Create Session**
```bash
curl -X POST http://localhost:8008/api/v1/ai/chat/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_title": "Shopping Help"
  }'
```

**Ask Question**
```bash
curl -X POST http://localhost:8008/api/v1/ai/chat/ask/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Điện thoại Samsung nào dưới 10 triệu?",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "..."
  }'
```

### User Preferences

**Get Preference Summary**
```bash
curl http://localhost:8008/api/v1/ai/users/550e8400-e29b-41d4-a716-446655440000/preferences/
```

Returns user's top brands, categories, price ranges, and purchase intent score.

## Data Models

### BehavioralEventModel
Events from user interactions with products/platform.
- Flexible product context (product_id, brand_name, category_name, price)
- Session tracking
- Source tracking
- Metadata support

### UserPreferenceProfileModel
Aggregated user preferences derived from events.
- JSON fields for scalability
- Brand/category/price range preferences with scores
- Purchase intent score (0-100)
- Last interaction timestamp

### KnowledgeDocumentModel
RAG knowledge base articles.
- 6 document types: faq, return_policy, payment_policy, shipping_policy, product_guide, support_article
- Automatic chunking
- Content + metadata

### KnowledgeChunkModel
Chunks for RAG retrieval.
- Linked to document
- Indexed chunks
- Vector embedding reference ready

### ChatSessionModel
User chat sessions for continuity.
- User tracking (nullable for anonymous)
- Session title
- Timestamps for archive logic

### ChatMessageModel  
Individual messages in session.
- Role: user, assistant, system
- Full message history
- Metadata for extensibility

## Configuration

### Environment Variables

```bash
# Django
SECRET_KEY=your-secret  
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Service
SERVICE_NAME=ai_service
SERVICE_PORT=8008

# Database (PostgreSQL)
DB_NAME=ai_service
DB_USER=ai_service
DB_PASSWORD=secure_password
DB_HOST=ai_service_db
DB_PORT=5432

# Redis (optional)
REDIS_URL=redis://redis:6379/0

# Neo4j (for future graph integration)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword

# LLM Provider
LLM_PROVIDER=mock  # mock|openai|anthropic
LLM_API_KEY=placeholder

# Logging
LOG_LEVEL=INFO
```

## Examples

### Preference-Based Recommendation Flow

```python
from uuid import uuid4
from modules.ai.application.services import (
    TrackBehavioralEventUseCase,
    GetUserPreferenceSummaryUseCase,
    GenerateRecommendationsUseCase,
)

# 1. Track user clicking Samsung multiple times
user_id = uuid4()
tracker = TrackBehavioralEventUseCase()
for _ in range(10):
    tracker.execute(
        event_type="product_click",
        user_id=user_id,
        brand_name="Samsung",
        category_name="Smartphone",
        price_amount=8990000,
    )

# 2. Get user preferences
pref_svc = GetUserPreferenceSummaryUseCase()
prefs = pref_svc.execute(user_id)
print(prefs["top_brands"])  # Samsung will be first

# 3. Generate recommendations
rec_svc = GenerateRecommendationsUseCase()
products = [
    {"id": "...", "name": "Samsung S24", "brand": "Samsung", "category": "Smartphone", "price": 20000000},
    {"id": "...", "name": "iPhone 15", "brand": "Apple", "category": "Smartphone", "price": 25000000},
    {"id": "...", "name": "Nokia 105", "brand": "Nokia", "category": "Smartphone", "price": 500000},
]
scored = rec_svc.score_products(products, user_id=user_id)
# Samsung S24 will score highest (preferred_brand + price nearby preference)
```

### Chat with Knowledge Base

```python
from modules.ai.application.services import (
    IngestKnowledgeDocumentUseCase,
    GenerateChatAnswerUseCase,
)

# 1. Add policy knowledge
ingest = IngestKnowledgeDocumentUseCase()
ingest.execute(
    title="Shipping Policy 2024",
    document_type="shipping_policy",
    content="Our shipping policy...",
)

# 2. Ask a question
chat = GenerateChatAnswerUseCase()
answer_data = chat.execute(
    query="Bao lâu tôi nhận hàng?",
    user_id=user_id,
)
print(answer_data["answer"])  # Answer from knowledge base + mock LLM
print(answer_data["sources"])  # Source documents
```

## Database Indexes

Optimized queries with practical indexes:
- `BehavioralEventModel`: (event_type, created_at), (user_id, created_at), (product_id), (price_range)
- `UserPreferenceProfileModel`: (purchase_intent_score), (updated_at)
- `KnowledgeChunkModel`: (document_id, chunk_index)
- `ChatSessionModel`: (user_id, updated_at)
- `ChatMessageModel`: (session_id, role, created_at)

## Admin Interface

Django admin provides management for:
- Behavioral events (search, filter, view)
- User profiles (inspect preferences, rebuild)
- Knowledge documents (CRUD, chunking status)
- Chat sessions and messages
- Recommendation cache

Access at `/admin/`

## Management Commands

### Seed Data
```bash
python manage.py seed_ai_data --users 10 --events-per-user 200
```

Generates demo scenario: users interact more with Samsung than Nokia, building preference profiles.

### Rebuild Profile
```bash
python manage.py shell
from uuid import UUID
from modules.ai.application.services import RebuildUserPreferenceProfileUseCase
use_case = RebuildUserPreferenceProfileUseCase()
use_case.execute(UUID('550e8400-e29b-41d4-a716-446655440000'))
```

## Testing

```bash
# Run all tests
python manage.py test modules.ai

# Run specific test
python manage.py test modules.ai.tests.TestBehavioralTracking

# With coverage
coverage run --source='modules.ai' manage.py test
coverage report
```

## Future Roadmap

### Phase 2: Advanced Features
- [ ] Real LLM integration (OpenAI, Anthropic,local models)
- [ ] Vector database (Chromadb, Weaviate, Pinecone)
- [ ] Neo4j real graph integration
- [ ] Collaborative filtering
- [ ] A/B testing framework
- [ ] Advanced chat memory/reasoning

### Phase 3: ML/AI Enhancements
- [ ] Graph embeddings (Node2Vec, GraphSAGE)
- [ ] Online learning (Bandits, Thompson sampling)
- [ ] Real-time personalization
- [ ] Content moderation
- [ ] Recommendation metrics dashboard

### Phase 4: Scale
- [ ] Streaming event processing
- [ ] Advanced analytics
- [ ] Multi-region deployment
- [ ] Cache strategies optimization

## Troubleshooting

**Events not tracked?**
- Verify payload JSON format
- Check event_type is valid
- Review database connection

**Profile not building?**
- Ensure valid UUID for user_id
- Check event_score calculation
- Verify database commits

**Recommendations empty?**
- Seed user with events first (`seed_ai_data`)
- Verify products list not empty
- Check no scoring errors in logs

**Chat not working?**
- Seed knowledge docs first
- Verify retrieval queries
- Check intent classification

## Support & Resources

- API Schema: `/api/schema/`
- Swagger UI: `/api/docs/`
- Django Admin: `/admin/`
- Health Check: `/health/`

## Port Mapping
- Application: `localhost:8008`
- Database: `ai_service_db:5432`
- Redis: `redis:6379`
- Neo4j: `neo4j:7687`

## License
See main project LICENSE.
- `modules/ai/application`: commands, queries, application services
- `modules/ai/infrastructure`: ORM models, repository implementations, querysets
- `modules/ai/presentation`: API serializers/views/controllers
