# TechShop

TechShop is a microservices-based e-commerce system built around Django services, a Next.js storefront, and an Nginx gateway. This repository is organized as a development monorepo: each service owns its API and database, while `docker-compose.yml` provides a full local environment for integration and demo work.

This README is the project overview. Service-level implementation details live in each service's own `README.md`.

## Overview

The platform is split into bounded services for identity, catalog, cart, order orchestration, payment, shipping, inventory, and AI-assisted experiences. The frontend consumes these APIs through the gateway rather than talking to services directly.

The codebase uses a consistent layered structure in most services:
- `domain`
- `application`
- `infrastructure`
- `presentation`

## Repository Map

```text
TechShop/
├── frontend/              # Next.js storefront and demo UI
├── gateway/               # Nginx gateway configuration
├── services/              # Django microservices
├── shared/                # Shared scripts, docs, and integration helpers
├── docker-compose.yml     # Local full-stack orchestration
├── .env.example           # Root environment template
└── README.md              # Project overview
```

## Service Map

| Component | Default Port | Responsibility |
| --- | ---: | --- |
| `frontend` | 3000 | Storefront UI and demo flows |
| `gateway` | 8080 | Reverse proxy and route entrypoint |
| `user_service` | 8001 | Authentication, users, profiles, addresses |
| `product_service` | 8002 | Catalog, products, brands, categories, variants |
| `cart_service` | 8003 | Shopping cart operations |
| `order_service` | 8004 | Order creation and orchestration |
| `payment_service` | 8005 | Payment processing workflows |
| `shipping_service` | 8006 | Shipment creation and tracking |
| `inventory_service` | 8007 | Stock and reservation management |
| `ai_service` | 8008 | Recommendations, event tracking, knowledge/chat APIs |
| `redis` | 6379 | Shared cache/infrastructure |
| `neo4j` | 7474 / 7687 | Optional graph infrastructure for AI-related work |

## Architecture Notes

- Each backend service is an independent Django project.
- Each service owns its own PostgreSQL database container.
- The gateway exposes service routes under path prefixes such as `/user/`, `/product/`, and `/ai/`.
- The frontend is a separate Next.js application and is also proxied through the gateway in the composed environment.
- Some parts of the platform are more complete than others. Use the service README and the code itself as the source of truth for implementation status.

## Current Technical Direction

- Backend: Python, Django, Django REST Framework
- Frontend: Next.js, TypeScript, Tailwind CSS
- Infra: Docker Compose, Nginx, PostgreSQL, Redis, Neo4j
- API docs: OpenAPI via `drf-spectacular`

The AI service currently includes recommendation, event tracking, document ingestion, graph sync, and chat-oriented APIs. Some provider and infrastructure dependencies remain environment-specific, so treat "AI" claims in older notes as implementation targets unless verified in code.

## Local Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ for local scripts
- Node.js if you want to run the frontend outside Docker

### Start the full stack

```bash
cp .env.example .env
docker compose up --build
```

### Seed demo data

```bash
python shared/scripts/seed_complete_system.py --verbose
```

### Basic verification

```bash
docker compose ps
curl http://localhost:8080/health
curl http://localhost:8001/health/
curl http://localhost:8002/api/docs/
curl http://localhost:8008/api/docs/
```

## Common Development Entry Points

- Frontend app: `http://localhost:3000`
- Gateway health: `http://localhost:8080/health`
- User service docs: `http://localhost:8001/api/docs/`
- Product service docs: `http://localhost:8002/api/docs/`
- Cart service docs: `http://localhost:8003/api/docs/`
- Order service docs: `http://localhost:8004/api/docs/`
- Payment service docs: `http://localhost:8005/api/docs/`
- Shipping service docs: `http://localhost:8006/api/docs/`
- Inventory service docs: `http://localhost:8007/api/docs/`
- AI service docs: `http://localhost:8008/api/docs/`

## Where To Read Next

- Read `AGENTS.md` first when working with an agent in this repository.
- Read `frontend/README.md` for storefront-specific guidance.
- Read the relevant service README before making backend changes:
- `services/user_service/README.md`
- `services/product_service/README.md`
- `services/cart_service/README.md`
- `services/order_service/README.md`
- `services/payment_service/README.md`
- `services/shipping_service/README.md`
- `services/inventory_service/README.md`
- `services/ai_service/README.md`
- Read `shared/docs/` for integration notes, demo flows, and seeding references.
