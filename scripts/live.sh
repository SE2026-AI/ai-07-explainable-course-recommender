#!/usr/bin/env sh
# Chạy thử live: PostgreSQL (Docker) + nạp dữ liệu + API ở http://127.0.0.1:8000. Chạy từ thư mục gốc repo.
# Máy đã có PostgreSQL khác chiếm cổng 5432 thì đặt POSTGRES_PORT, ví dụ: POSTGRES_PORT=55432 sh scripts/live.sh
set -e
PORT="${POSTGRES_PORT:-5432}"
POSTGRES_PORT="$PORT" docker compose -f build/deploy/docker-compose.yml up -d --wait db
export DATABASE_URL="postgresql+psycopg://coursereco:coursereco@localhost:$PORT/course_recommender"
python -m tools.build_db
exec python -m uvicorn src.api.main:app --port 8000
