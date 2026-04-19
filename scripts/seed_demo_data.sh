#!/usr/bin/env sh
set -eu

python scripts/generate_demo_ai_assets.py
python shared/scripts/seed_complete_system.py --verbose
docker compose exec -T ai_service python manage.py load_ai_dataset --replace-demo
docker compose exec -T ai_service python manage.py build_rag_index --replace
docker compose exec -T ai_service python manage.py train_lstm_recommender --dataset /app/data/data_100users.csv
