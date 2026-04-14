# shipping_service

## Purpose
Owns shipment creation, carrier integration boundaries, and delivery workflow orchestration.

This repository is only the foundation skeleton for the service. Business use cases, aggregates, repositories, and workflows will be implemented in later phases.

## Local Run
1. Copy `.env.example` to `.env`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the server:
   ```bash
   python manage.py runserver 0.0.0.0:8006
   ```

## Environment Variables
- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `SERVICE_PORT`
- `REDIS_URL`
- `SERVICE_NAME`
- `UPSTREAM_TIMEOUT`
- `CORS_ALLOW_ALL_ORIGINS`

## Endpoints
- `GET /health/`
- `GET /ready/`
- `GET /api/v1/health/`
- `GET /api/schema/`
- `GET /api/docs/`

## Port Mapping
- Application: `localhost:8006`
- Database: `localhost:5438`

## DDD Structure
- `modules/shipping/domain`: entities, value objects, repository contracts
- `modules/shipping/application`: commands, queries, application services
- `modules/shipping/infrastructure`: ORM models, repository implementations, querysets
- `modules/shipping/presentation`: API serializers/views/controllers
