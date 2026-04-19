#!/usr/bin/env sh
set -eu

python scripts/generate_demo_ai_assets.py
docker compose exec -T ai_service python manage.py train_lstm_recommender --dataset /app/data/data_100users.csv
