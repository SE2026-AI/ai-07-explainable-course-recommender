# AI-07 Explainable Course Recommender — Vertical Slice VT-097 (Plan Undo)

- **Sinh viên thực hiện:** Phạm Hữu Hưng — MSV: `22001597`
- **Nhóm:** `SE2026-T24` (`SE.2026.14`) — Vai trò: Nhóm trưởng
- **Mã biến thể:** `VT-097` (Bài tập cá nhân 3)
- **Nhánh làm việc:** `feat/vt097-plan-undo` (tách từ baseline `main@30fd287`, ngày 06/11/2026)
- **Trạng thái PR:** Chờ nhóm review (Không tự merge vào `main` khi chưa có review của thành viên khác).

## 1. Chuỗi 3 Commits tái lập đúng vòng lặp TDD & Mutation Testing trên nhánh `feat/vt097-plan-undo`
1. **Commit 1 (`test(vt097): add baseline plan_undo stub, mount router in create_app, and add 11 BVA tests`)**:
   - Đăng ký `plan_undo.router` vào bên trong `create_app()` của `src/api/app.py` với `prefix=prefix` (`1 file changed, 2 insertions(+), 1 deletion(-)`).
   - Tự động chạy `python3 -m tools.export_openapi` để đồng bộ `docs/api/openapi.json` (vượt qua `test_openapi_matches_committed_file`).
   - Tạo bản cài đặt baseline stub tại `src/rules/plan_undo.py`, router `src/api/routers/plan_undo.py` và bộ **11 test cases ban đầu (`TC-01..TC-11`)** tại `test/test_plan_undo.py`.
   - Khi chạy test ở Commit 1 (Red Phase): 3 test biên dương cơ bản (`TC-01, TC-02, TC-06`) `ok`, **8 test biên âm/failure/auth (`TC-03..05, TC-07..11`) `FAIL`** (`Ran 11 tests ... FAILED (failures=8)`).
2. **Commit 2 (`feat(plan-undo): enforce BVA validation, 24-credit limit, and dual-path auth`)**:
   - Áp dụng bản vá AI Minimal Patch lên `src/rules/plan_undo.py` (`1 file changed, 156 insertions(+), 43 deletions(-)`).
   - Khi chạy lại bộ 11 test cases ở Commit 2 (Green Phase): **11/11 tests PASS (`Ran 11 tests ... OK`)**.
3. **Commit 3 (`test(vt097): add TC-12 explicit token IDOR test to kill auth mutation and add 60-user load harness`)**:
   - Sau khi thực hiện thí nghiệm Mutation trên nhánh tạm (xóa kiểm tra quyền ở Đường đi 2 tại dòng 210–211 khi truyền `undo_token` và phát hiện 11 test đầu đều PASS làm mutation sống sót), bổ sung **`TC-12` (`test_tc12_api_undo_by_explicit_token_rejects_cross_user_idor`, `+33 insertions`)** để tiêu diệt mutation (`FAILED (failures=1): 200 != 403`), kèm kịch bản kiểm thử tải 2 chế độ `test/load_test_vt097.py` và `README_VT097.md`.
   - Khi chạy bộ test hoàn chỉnh ở Commit 3: **12/12 tests PASS (`Ran 12 tests ... OK`)**, `ruff check .` báo `0 errors`.

## 2. Hướng dẫn chạy Test, Coverage & Kiểm chứng tải
```bash
# 1. Chạy bộ 12 Unit & API Integration Tests (BVA):
PYTHONPATH=. python3 -m unittest discover -s test -p "test_plan_undo.py" -v
# Hoặc bằng pytest kèm đo Branch Coverage:
PYTHONPATH=. pytest test/test_plan_undo.py --cov=src.rules.plan_undo --cov=src.api.routers.plan_undo --cov-branch --cov-report=term-missing -v

# 2. Kiểm tra chuẩn lint Ruff và hợp đồng OpenAPI:
ruff check .
PYTHONPATH=. pytest test/test_api.py -k "test_openapi_matches_committed_file"

# 3. Chạy thực nghiệm tải 60 người dùng/tác vụ đồng thời (cả 2 chế độ có sleep & không sleep) và Concurrency Race 20 luồng:
PYTHONPATH=. python3 test/load_test_vt097.py
```
