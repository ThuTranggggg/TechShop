# product_service

## Purpose
Owns the catalog bounded context for products, categories, attributes, media, and discovery metadata.

This service owns the product catalog bounded context end-to-end, including categories, products, validation, query/filter logic, migrations, and seed data.

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
5. Seed sample catalog data:
   ```bash
   python manage.py seed_catalog
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
- `GET /api/v1/catalog/categories/`
- `GET /api/v1/catalog/categories/{id|slug}/`
- `GET /api/v1/catalog/categories/{id|slug}/products/`
- `GET /api/v1/catalog/products/`
- `GET /api/v1/catalog/products/{id|slug}/`
- `GET /api/v1/catalog/admin/categories/`
- `GET|POST|PATCH|DELETE /api/v1/catalog/admin/products/`
- `GET /api/schema/`
- `GET /api/docs/`

## Port Mapping
- Application: `localhost:8002`
- Database: `localhost:5434`

## DDD Structure
- `modules/catalog/domain`: entities, value objects, repository contracts
- `modules/catalog/application`: commands, queries, DTOs, seed definitions, application services
- `modules/catalog/infrastructure`: ORM models and repository implementations
- `modules/catalog/presentation`: API serializers/views/controllers
