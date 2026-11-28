# Chạy thử live: PostgreSQL (Docker) + nạp dữ liệu + API ở http://127.0.0.1:8000. Chạy từ thư mục gốc repo.
# Máy đã có PostgreSQL khác chiếm cổng 5432 thì đặt cổng khác: $env:POSTGRES_PORT = "55432" trước khi chạy.
$ErrorActionPreference = "Stop"
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5432" }
# Project/volume riêng: không nạp lại database coursereco đang dùng ở nơi khác.
docker compose -p ai07-live -f build/deploy/docker-compose.yml up -d --wait db
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:DATABASE_URL = "postgresql+psycopg://coursereco:coursereco@localhost:$($env:POSTGRES_PORT)/course_recommender"
python -m tools.build_db
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m uvicorn src.api.main:app --port 8000
