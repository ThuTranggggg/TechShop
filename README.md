# TechShop

TechShop is a microservices e-commerce platform built around Django services, a Next.js storefront, and an Nginx gateway. Each backend service owns its own API and database, and the frontend talks to services through the gateway rather than directly.

## Overview

The repository is organized as a development monorepo:

- `frontend/` - Next.js storefront and demo UI
- `gateway/` - Nginx routing layer
- `services/` - Django-based backend services
- `shared/` - scripts, docs, and assignment artefacts

The platform includes identity, catalog, cart, order, payment, shipping, inventory, and AI-assisted experiences. The AI service covers behavioral tracking, recommendations, knowledge retrieval, graph sync, and chat flows.

## Service Map

| Component | Port | Responsibility |
| --- | ---: | --- |
| `frontend` | 3000 | Storefront UI and demo flows |
| `gateway` | 8080 | Reverse proxy and route entrypoint |
| `user_service` | 8001 | Authentication, users, profiles, addresses |
| `product_service` | 8002 | Catalog, products, brands, categories |
| `cart_service` | 8003 | Shopping cart operations |
| `order_service` | 8004 | Order creation and orchestration |
| `payment_service` | 8005 | Payment workflows |
| `shipping_service` | 8006 | Shipment creation and tracking |
| `inventory_service` | 8007 | Stock and reservation management |
| `ai_service` | 8008 | Recommendations, event tracking, graph, RAG chat |
| `redis` | 6379 | Shared cache and background support |
| `neo4j` | 7474 / 7687 | Optional graph database for AI workflows |

## Architecture

- Each backend service is an independent Django project.
- Each service owns its own PostgreSQL database container.
- The gateway exposes routes such as `/user/`, `/product/`, and `/ai/`.
- The frontend is a separate Next.js application and is proxied through the gateway in the composed environment.
- Some features are intentionally environment-dependent. Use the code and service READMEs as the source of truth for implementation status.

## Local Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ for local scripts
- Node.js if you want to run the frontend outside Docker

### Start the stack

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

## Where To Read Next

- Read `AGENTS.md` first when working with an agent in this repository.
- Read `frontend/README.md` for storefront guidance.
- Read the relevant service README before making backend changes.
- Read `shared/docs/` for integration notes, demo flows, and seeding references.
