"""Xuất OpenAPI spec ra file JSON ổn định.

Chạy: python -m tools.export_openapi

File đầu ra: docs/api/openapi.json

Quy ước để kết quả ổn định giữa các lần chạy:
- indent=2
- ensure_ascii=False
- sort_keys=True
- Xuống dòng ở cuối file
"""
from __future__ import annotations

import json
import pathlib

from src.api.app import create_app

OUTPUT = pathlib.Path("docs/api/openapi.json")


def main() -> None:
    """Sinh openapi.json từ app FastAPI hiện tại."""
    # Tạo app không kết nối DB (không có query ở import-time)
    app = create_app()

    # Trigger generate openapi schema
    schema = app.openapi()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Written: {OUTPUT} ({len(content)} bytes, {len(schema['paths'])} paths)")


if __name__ == "__main__":
    main()
