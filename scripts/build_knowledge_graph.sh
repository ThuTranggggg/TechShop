#!/usr/bin/env sh
set -eu

python scripts/generate_demo_ai_assets.py
docker compose exec -T ai_service python manage.py load_ai_dataset --replace-demo --skip-knowledge --skip-graph
docker compose exec -T ai_service python manage.py rebuild_knowledge_graph --clear
