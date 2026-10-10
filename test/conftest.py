"""Dựng cơ sở dữ liệu kiểm thử một lần cho cả phiên test.

Mỗi fixture tạo một database PostgreSQL TẠM (tên tmp_coursereco_…), nạp CSV, và xóa khi test xong,
nên không bao giờ đụng vào database đang dùng.
- `repo`: dữ liệu thật của dự án = data/seed + data/synthetic
- `repo_all`: thêm trường giả lập DEMO và sinh viên kiểm thử (test/fixtures)
Máy chủ lấy từ TEST_DATABASE_URL, nếu không có thì DATABASE_URL (xem docs/setup.md).
"""
import os

import pytest

from src.data.db.build import scratch_build
from src.data.repository import Repository

MAIN = ["data/seed", "data/synthetic"]
ALL = MAIN + ["test/fixtures/seed_demo", "test/fixtures/students"]
SERVER = os.environ.get("TEST_DATABASE_URL")          # None -> DATABASE_URL -> mặc định docker-compose


@pytest.fixture(scope="session")
def repo():
    with scratch_build(MAIN, SERVER) as engine:
        yield Repository(engine=engine)


@pytest.fixture(scope="session")
def repo_all():
    with scratch_build(ALL, SERVER) as engine:
        yield Repository(engine=engine)


def curricula_codes():
    import pandas as pd
    return list(pd.read_csv("data/seed/curricula.csv")["code"]) + ["DEMO-7480201-2024"]
