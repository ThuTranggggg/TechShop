.PHONY: build up down logs ps setup seed train-lstm build-kg build-rag dev test smoke

build:
	docker compose build

up:
	docker compose up --build

setup:
	python scripts/generate_demo_ai_assets.py

seed:
	sh scripts/seed_demo_data.sh

train-lstm:
	sh scripts/train_models.sh

build-kg:
	sh scripts/build_knowledge_graph.sh

build-rag:
	sh scripts/build_rag_index.sh

dev:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test:
	docker compose run --rm user_service python manage.py test

smoke:
	python scripts/smoke_test.py
