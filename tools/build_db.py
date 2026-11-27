"""Tạo cơ sở dữ liệu từ CSV.

Máy phát triển và kiểm thử:

    python -m tools.build_db                         # DATABASE_URL (seed + synthetic), tạo lại bảng tham chiếu
    python -m tools.build_db --url postgresql+psycopg://user:pass@host:5432/db
    python -m tools.build_db --dirs data/seed        # chỉ dữ liệu tham chiếu
    python -m tools.build_db --drop-user-data        # xóa luôn tài khoản, bảng điểm, kế hoạch đang có

Production: chỉ nạp data/seed, không bao giờ đụng bảng người dùng (docs/architecture/data-model.md mục 8):

    python -m tools.build_db --production                      # lần đầu: migrate rồi nạp data/seed
    python -m tools.build_db --production --reload-reference   # thay dữ liệu tham chiếu đang có bằng data/seed
"""
import argparse
import sys

from src.data.db.build import build, get_engine, reference_loaded, reload_reference
from src.data.db.migrate import migrate

PRODUCTION_DIRS = ["data/seed"]


def _production(url, reload):
    for step in migrate(url):
        print(f"migrate: {step}")
    engine = get_engine(url)
    try:
        if reference_loaded(engine) and not reload:
            print("Database đã có dữ liệu tham chiếu, không nạp lại. Khung admin thêm qua API sẽ mất nếu nạp đè từ "
                  "data/seed; chỉ làm vậy khi chắc chắn, bằng --reload-reference.", file=sys.stderr)
            return {}, 1
        return reload_reference(engine, PRODUCTION_DIRS), 0
    finally:
        engine.dispose()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="mặc định: biến môi trường DATABASE_URL")
    ap.add_argument("--dirs", nargs="+", default=["data/seed", "data/synthetic"])
    ap.add_argument("--drop-user-data", action="store_true",
                    help="máy phát triển: xóa cả bảng người dùng khi tạo lại")
    ap.add_argument("--production", action="store_true",
                    help="migrate rồi chỉ nạp data/seed, giữ nguyên bảng người dùng; bỏ qua --dirs")
    ap.add_argument("--reload-reference", action="store_true",
                    help="với --production: thay dữ liệu tham chiếu đang có bằng data/seed")
    a = ap.parse_args()
    if a.production:
        dem, code = _production(a.url, a.reload_reference)
    else:
        engine, dem = build(a.url, a.dirs, drop_user_data=a.drop_user_data)
        engine.dispose()
        code = 0
    for k, v in dem.items():
        print(f"{k:28s}{v:>6}")
    sys.exit(code)


if __name__ == "__main__":
    main()
