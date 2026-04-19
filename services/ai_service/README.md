# AI Service

AI Service cho tu van san pham va goi y ca nhan hoa theo mo hinh hybrid:

- User behavior tracking: `search`, `click`, `add_to_cart`, `chat_query`, `payment_success`...
- LSTM sequence modeling: du doan san pham tiep theo tu chuoi hanh vi
- Neo4j knowledge graph: `User`, `Product`, `ProductGroup`, `Category`, `Keyword`, `SIMILAR`
- RAG retrieval: truy hoi knowledge documents de chatbot tra loi dung ngu canh
- Hybrid scoring: `final_score = w_profile + w_lstm + w_graph + w_rag`

## Kien truc

Input:
- User behavior data
- Query tu chatbot

Processing:
- LSTM: du doan next product theo chuoi hanh vi
- Graph: khai thac quan he mua/xem/tuong tu bang Neo4j
- RAG: truy hoi tri thuc tu knowledge base

Output:
- Recommendation list
- Chatbot tu van san pham

## Dataset CSV

Tat ca dataset mau nam trong `services/ai_service/data/`:

- [product_catalog.csv](/f:/Semester8/04_KT&TK/TechShop/services/ai_service/data/product_catalog.csv)
- [user_behavior.csv](/f:/Semester8/04_KT&TK/TechShop/services/ai_service/data/user_behavior.csv)
- [product_relations.csv](/f:/Semester8/04_KT&TK/TechShop/services/ai_service/data/product_relations.csv)
- [knowledge_documents.csv](/f:/Semester8/04_KT&TK/TechShop/services/ai_service/data/knowledge_documents.csv)

`user_behavior.csv` dung dung theo yeu cau bai toan:

```csv
user_id,product_slug,action,timestamp
11111111-1111-4111-8111-111111111111,smartphone-nova-5g,product_view,2026-04-01T08:03:00+07:00
11111111-1111-4111-8111-111111111111,smartphone-nova-5g,add_to_cart,2026-04-01T08:10:00+07:00
```

Khi import, service se map `product_slug` sang `product_id` that su trong `product_service`, luu event vao PostgreSQL va sync qua Neo4j.

## Neo4j Graph Model

Node:
- `User`
- `Product`
- `ProductGroup`
- `Category`
- `Keyword`

Relationship:
- `VIEWED`
- `CLICKED`
- `ADDED_TO_CART`
- `ORDERED`
- `PAID`
- `INTERESTED_IN_GROUP`
- `INTERESTED_IN_CATEGORY`
- `SEARCHED_KEYWORD`
- `SIMILAR`

## API

### 1. Recommendation List

GET recommendation theo user va query:

```bash
curl "http://localhost:8008/api/v1/ai/recommend/?user_id=11111111-1111-4111-8111-111111111111&query=dien%20thoai%20duoi%2010%20trieu&limit=5"
```

POST scoring cho danh sach products da co:

```bash
curl -X POST http://localhost:8008/api/v1/ai/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "11111111-1111-4111-8111-111111111111",
    "query": "dien thoai duoi 10 trieu",
    "products": [
      {"id": "uuid", "name": "Smartphone Nova 5G", "brand": "dien tu", "category": "dien thoai va may tinh bang", "price": 8990000}
    ]
  }'
```

Response co:
- `score`
- `reason_codes`
- `component_scores.profile`
- `component_scores.lstm`
- `component_scores.graph`
- `component_scores.rag`

### 2. Chatbot Tu Van

```bash
curl -X POST http://localhost:8008/api/v1/ai/chat/ask/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "11111111-1111-4111-8111-111111111111",
    "query": "toi can dien thoai gia duoi 10 trieu"
  }'
```

Chatbot se:
1. Classify intent
2. Extract product group/category/price entities
3. Retrieve knowledge documents
4. Lay candidate products tu catalog
5. Score bang hybrid model
6. Tra ve cau tra loi + related products

## Management Commands

Import dataset CSV vao PostgreSQL + Neo4j:

```bash
python manage.py load_ai_dataset --replace-demo --reset-graph --train-lstm
```

Train lai sequence model rieng:

```bash
python manage.py train_lstm_recommender
```

Seed demo cu nhanh gon:

```bash
python manage.py seed_ai_data
```

## LSTM Model

Implementation nam trong:
- [sequence_models.py](/f:/Semester8/04_KT&TK/TechShop/services/ai_service/modules/ai/infrastructure/sequence_models.py)

Model artifact mac dinh:
- `data/models/lstm_recommender.pt`
- `data/models/sequence_model_metadata.json`

Neu moi truong chua co `torch`, command train van sinh metadata transition fallback de service khong bi dung.

## Luong Import CSV

`load_ai_dataset` thuc hien:
1. Doc `product_catalog.csv`
2. Map `slug -> product_id` tu `product_service`
3. Import `knowledge_documents.csv` vao RAG store
4. Import `user_behavior.csv` vao PostgreSQL
5. Sync event va product graph sang Neo4j
6. Import `SIMILAR` edges tu `product_relations.csv`
7. Rebuild preference profile
8. Train LSTM neu bat `--train-lstm`

## Tech Stack

- Django REST Framework
- PostgreSQL
- Neo4j
- PyTorch
- httpx

## Kiem tra nhanh

```bash
curl http://localhost:8008/health/
curl http://localhost:8008/api/v1/ai/users/11111111-1111-4111-8111-111111111111/preferences/
curl "http://localhost:8008/api/v1/ai/recommend/?user_id=11111111-1111-4111-8111-111111111111&query=smartphone"
```

## Ghi chu

- Truong `brand_name` trong he thong hien duoc dung nhu `product group` de phu hop catalog da nganh.
- Recommendation hien dang uu tien catalog that tu `product_service`, khong dung product id gia trong CSV.
- Chatbot tu dong track `chat_query` vao behavior log de bo sung ngu canh cho lan goi y tiep theo.
