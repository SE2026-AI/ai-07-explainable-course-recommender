"""Xuất câu lệnh CREATE TABLE/INDEX/VIEW của PostgreSQL để đọc, review hoặc chạy tay.

Chạy: python -m tools.export_schema   ->  data/schema/schema_postgresql.sql
"""
import os

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from src.data.db.schema import metadata
from src.data.db.views import VIEWS


def export(dialect, path):
    parts = [f"-- Sinh tự động từ src/data/db/schema.py – KHÔNG sửa tay. Hệ quản trị: {dialect.name}\n"]
    for t in metadata.sorted_tables:
        if t.comment:
            parts.append(f"-- {t.name}: {t.comment}")
        parts.append(str(CreateTable(t).compile(dialect=dialect)).strip() + ";\n")
        for ix in sorted(t.indexes, key=lambda i: i.name):
            parts.append(str(CreateIndex(ix).compile(dialect=dialect)).strip() + ";")
        parts.append("")
    for name, sql in VIEWS.items():
        parts.append(f"CREATE VIEW {name} AS{sql.rstrip()};\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    os.makedirs("data/schema", exist_ok=True)
    export(postgresql.dialect(), "data/schema/schema_postgresql.sql")
    print("Đã xuất data/schema/schema_postgresql.sql")


if __name__ == "__main__":
    main()
