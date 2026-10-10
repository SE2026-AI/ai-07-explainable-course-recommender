"""Tạo cơ sở dữ liệu từ CSV.

    python -m tools.build_db                         # DATABASE_URL (seed + synthetic), XÓA và tạo lại bảng
    python -m tools.build_db --url postgresql+psycopg://user:pass@host:5432/db
    python -m tools.build_db --dirs data/seed        # chỉ dữ liệu tham chiếu
"""
import argparse

from src.data.db.build import build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="mặc định: biến môi trường DATABASE_URL")
    ap.add_argument("--dirs", nargs="+", default=["data/seed", "data/synthetic"])
    a = ap.parse_args()
    _, dem = build(a.url, a.dirs)
    for k, v in dem.items():
        print(f"{k:28s}{v:>6}")


if __name__ == "__main__":
    main()
