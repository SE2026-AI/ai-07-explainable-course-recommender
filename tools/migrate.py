"""Đưa lược đồ database lên bản mới nhất bằng Alembic, không mất dữ liệu.

    python -m tools.migrate                          # DATABASE_URL
    python -m tools.migrate --url postgresql+psycopg://user:pass@host:5432/db

Chạy được trên database trống, database dựng bằng tools.build_db của v1 (lược đồ 3.0.0) và database đã migrate
trước đó (src/data/db/migrate.py). Tạo migration mới sau khi sửa src/data/db/schema.py: data-model.md mục 9.
"""
import argparse

from src.data.db.migrate import current_revision, migrate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="mặc định: biến môi trường DATABASE_URL")
    a = ap.parse_args()
    for step in migrate(a.url) or ["đã ở bản mới nhất"]:
        print(step)
    print(f"phiên bản hiện tại: {current_revision(a.url)}")


if __name__ == "__main__":
    main()
