"""Sinh một migration Alembic mới sau khi sửa src/data/db/schema.py (docs/architecture/data-model.md mục 9).

    python -m tools.new_migration "them cot x vao bang y"

Tự dựng một database tạm, nâng nó lên migration mới nhất, so với schema.py rồi ghi phần chênh vào
migrations/versions/NNNN_<mô tả>.py với số thứ tự kế tiếp, và chạy `ruff format` cho file đó. Không đụng database
đang dùng. Đọc lại file sinh ra trước khi commit: autogenerate không thấy được đổi tên bảng, đổi tên cột hay sửa
view, những thứ đó phải viết tay.
"""
import argparse
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory

from src.data.db.build import temporary_database
from src.data.db.migrate import ROOT, alembic_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message", help="mô tả ngắn, không dấu, ví dụ: them bang thong bao")
    a = ap.parse_args()
    with temporary_database() as url:
        cfg = alembic_config(url)
        head = ScriptDirectory.from_config(cfg).get_current_head()
        rev_id = f"{int(head or 0) + 1:04d}"
        command.upgrade(cfg, "head")
        script = command.revision(cfg, message=a.message, autogenerate=True, rev_id=rev_id)
    path = Path(script.path)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(path)], cwd=ROOT, check=False)
    print(f"Đã tạo {path.relative_to(ROOT)}: đọc lại, sửa docstring, rồi chạy pytest test/test_migrations.py")


if __name__ == "__main__":
    main()
