# TechShop

TechShop là hệ thống e-commerce microservices gồm frontend Next.js, backend Django/DRF, PostgreSQL theo từng service, Redis, Neo4j và `ai_service` phục vụ recommendation, behavior analytics, LSTM, Knowledge Graph và RAG chat.

## Stack hiện tại

- Frontend: Next.js 14, TypeScript, Tailwind, React Query
- Backend: Django 5 + Django REST Framework cho `user`, `product`, `cart`, `order`, `payment`, `shipping`, `inventory`, `ai`
- Database: PostgreSQL riêng cho từng service
- Infra: Redis, Neo4j, Nginx gateway, Docker Compose
- Auth/RBAC: JWT + roles `admin`, `staff`, `customer`
- AI: behavioral events, recommendation hybrid, PyTorch LSTM fallback, Neo4j KG, local keyword/vector-lite RAG fallback

## Những gì đã có sau khi cập nhật

- Roles đầy đủ: `Admin`, `Staff`, `Customer`
- Catalog seed 45 sản phẩm, đa category:
  - `electronics`
  - `fashion`
  - `cosmetics`
  - `home_appliances`
  - `accessories`
  - `books`
  - `groceries`
  - `sports`
  - và thêm `baby_kids`, `furniture`, `office`, `toys`
- Flow chạy end-to-end:
  - search/view product
  - add to cart / update cart
  - checkout
  - create order
  - mock payment success/failure
  - auto create shipment sau payment success
  - staff/admin update shipping status
- AI service:
  - recommendations
  - search
  - add-to-cart action
  - create-order action
  - chat + RAG
  - behavior analytics
  - KG rebuild
  - LSTM training endpoint/script
- Dữ liệu AI:
  - `data_100users.csv`
  - hơn 3.000 behavior events
  - tối thiểu 10 loại hành vi

## Cấu trúc quan trọng

```text
frontend/                               Next.js app demo
gateway/                                Nginx gateway
services/
  user_service/                         auth + users + roles
  product_service/                      catalog + categories + brands
  cart_service/                         cart
  order_service/                        orders + orchestration
  payment_service/                      mock payment
  shipping_service/                     shipping + tracking + staff ops
  inventory_service/                    stock + reservations
  ai_service/                           recommendations + behavior + KG + RAG + LSTM
scripts/
  generate_demo_ai_assets.py            sinh data_100users + AI assets
  seed_demo_data.sh                     seed demo toàn hệ thống
  train_models.sh                       train LSTM
  build_knowledge_graph.sh              rebuild Neo4j KG
  build_rag_index.sh                    rebuild RAG index
  smoke_test.py                         smoke test end-to-end
data/
  data_100users.csv                     dữ liệu behavior 100 users
  faq/                                  tài liệu FAQ cho RAG
  policies/                             shipping/payment/return policy
```

## Tài khoản demo

- Admin: `admin@techshop.com` / `Demo@123456`
- Staff: `staff@techshop.com` / `Demo@123456`
- Customer: `john@example.com` / `Demo@123456`

## Chạy bằng Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Sau khi các container lên xong:

```bash
python scripts/generate_demo_ai_assets.py
sh scripts/seed_demo_data.sh
```

Truy cập:

- Frontend: `http://localhost:3000`
- Gateway: `http://localhost:8080`
- Swagger docs:
  - `http://localhost:8001/api/docs/`
  - `http://localhost:8002/api/docs/`
  - `http://localhost:8008/api/docs/`
- Neo4j Browser: `http://localhost:7474`

## Seed dữ liệu

### 1. Sinh file AI demo

```bash
python scripts/generate_demo_ai_assets.py
```

Sinh ra:

- `data_100users.csv`
- `data/data_100users.csv`
- `services/ai_service/data/data_100users.csv`
- `services/ai_service/data/user_behavior.csv`
- `services/ai_service/data/product_catalog.csv`
- `services/ai_service/data/product_relations.csv`
- `services/ai_service/data/knowledge_documents.csv`

### 2. Seed toàn hệ thống

```bash
sh scripts/seed_demo_data.sh
```

Script này sẽ:

1. sinh AI assets
2. seed users / products / carts / orders / inventory
3. load AI behavior dataset vào `ai_service`
4. build RAG index
5. train LSTM

## Train LSTM

```bash
sh scripts/train_models.sh
```

Hoặc gọi trực tiếp:

```bash
docker compose exec -T ai_service python manage.py train_lstm_recommender --dataset /app/data/data_100users.csv
```

Artifacts:

- `/app/data/models/lstm_recommender.pt`
- `/app/data/models/sequence_model_metadata.json`

## Build Knowledge Graph

```bash
sh scripts/build_knowledge_graph.sh
```

Hoặc:

```bash
docker compose exec -T ai_service python manage.py rebuild_knowledge_graph --clear
```

Neo4j nodes/relations được build từ:

- live product catalog
- behavioral events
- order links từ metadata trong `data_100users.csv`
- product similarity edges từ `product_relations.csv`

## Build RAG Index

```bash
sh scripts/build_rag_index.sh
```

Hoặc:

```bash
docker compose exec -T ai_service python manage.py build_rag_index --replace
```

Nguồn tri thức:

- `data/faq/*.md`
- `data/policies/*.md`
- `services/ai_service/data/knowledge_documents.csv`
- live catalog grouped by category

## Smoke test nhanh

```bash
python scripts/smoke_test.py
```

Script kiểm tra các bước:

1. login role customer
2. list/search products
3. add to cart
4. create order
5. mock payment success
6. staff update shipping status
7. recommendations
8. behavior summary
9. KG rebuild
10. LSTM train
11. RAG rebuild
12. chat trả lời được

## API chính

### Auth / User

- `POST /user/api/v1/auth/register/`
- `POST /user/api/v1/auth/login/`
- `GET /user/api/v1/auth/me/`

### Products

- `GET /product/api/v1/catalog/products/`
- `GET /product/api/v1/catalog/products/{id}/`
- `GET /product/api/v1/catalog/categories/`

### Cart

- `GET /cart/api/v1/cart/current/`
- `POST /cart/api/v1/cart/items/`
- `PATCH /cart/api/v1/cart/items/{id}/quantity/`
- `DELETE /cart/api/v1/cart/items/{id}/`

### Orders

- `POST /order/api/v1/orders/from-cart/`
- `GET /order/api/v1/orders/`
- `GET /order/api/v1/orders/{id}/`
- `GET /order/api/v1/operations/orders/` (`staff/admin`)

### Payments

- `POST /payment/api/v1/payments/`
- `POST /payment/api/v1/webhooks/mock/`
- `GET /payment/api/v1/payments/{reference}/status/`

### Shipping

- `GET /shipping/api/v1/shipments/{reference}/tracking/`
- `GET /shipping/api/v1/operations/shipments/order/{orderId}/`
- `PATCH /shipping/api/v1/operations/shipments/order/{orderId}/status/` (`staff/admin`)

### AI

- `GET /ai/api/v1/ai/recommendations/{userId}/`
- `POST /ai/api/v1/ai/recommendations/`
- `GET /ai/api/v1/ai/search/?q=...`
- `GET /ai/api/v1/ai/behavior/summary/`
- `GET /ai/api/v1/ai/behavior/users/{userId}/`
- `GET /ai/api/v1/ai/behavior/funnel/`
- `POST /ai/api/v1/ai/actions/add-to-cart/`
- `POST /ai/api/v1/ai/actions/create-order/`
- `POST /ai/api/v1/ai/chat/`
- `POST /ai/api/v1/ai/kg/rebuild/`
- `POST /ai/api/v1/ai/lstm/train/`
- `POST /ai/api/v1/ai/rag/rebuild/`

## Frontend demo path

1. `/login` hoặc `/register`
2. `/products` để search/filter catalog
3. `/products/{id}` để xem chi tiết và add to cart
4. `/cart` -> `/checkout` -> `/orders/{id}`
5. `/chat` để demo RAG
6. `/admin` với admin/staff để:
   - quản lý products
   - xem behavior analytics
   - trigger KG/RAG/LSTM
   - cập nhật shipping status

## Chạy local từng service nếu cần

Ví dụ `ai_service`:

```bash
cd services/ai_service
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8008
```

## Ghi chú fallback

- Nếu không có external LLM API key, chat vẫn chạy bằng local/mock provider + retrieval từ knowledge chunks.
- Nếu PyTorch không khả dụng, LSTM service sẽ fallback sang transition matrix metadata để recommendation vẫn hoạt động.
- Nếu Neo4j chưa sẵn sàng, app vẫn chạy; graph scoring sẽ fallback an toàn.
