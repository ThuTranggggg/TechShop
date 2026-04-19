#!/usr/bin/env sh
set -eu

python scripts/generate_demo_ai_assets.py
docker compose exec -T ai_service python manage.py build_rag_index --replace
