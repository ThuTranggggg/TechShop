.PHONY: build up down logs ps test

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test:
	docker compose run --rm user_service python manage.py test
