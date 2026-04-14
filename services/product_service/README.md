# product_service

## Purpose
Owns the catalog bounded context for products, categories, attributes, media, and discovery metadata.

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
   python manage.py runserver 0.0.0.0:8002
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
- Application: `localhost:8002`
- Database: `localhost:5434`

## DDD Structure
- `modules/catalog/domain`: entities, value objects, repository contracts
- `modules/catalog/application`: commands, queries, application services
- `modules/catalog/infrastructure`: ORM models, repository implementations, querysets
- `modules/catalog/presentation`: API serializers/views/controllers
