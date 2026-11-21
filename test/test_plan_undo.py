"""
Bộ kiểm thử tự động cho biến thể VT-097 (Phạm Hữu Hưng - 22001597) trên dự án AI-07 (main@30fd287).
Áp dụng kỹ thuật Boundary Value Analysis (BVA), Negative Testing và Failure-Path Testing.
"""
from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_handlers
from src.api.routers import plan_undo
from src.api.routers.plan_undo import undo_service
from src.api.serialization import CleanJSONResponse
from src.api.version import API_VERSION
from src.rules.plan_undo import (
    PlanUndoConflictError,
    PlanUndoService,
    PlanUndoValidationError,
)


class FakeClock:
    def __init__(self, initial: float = 1000.0) -> None:
        self.now = initial

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestPlanUndoVT097(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(1000.0)
        self.svc = PlanUndoService(clock_fn=self.clock)
        self.uni = "HUS"
        self.student_code = "22001597"
        self.term_code = "20261"
        # Seed 10 môn (20 TC), có chứa cả biên dưới hợp lệ L=3 ("ABC") và biên trên L=16 ("HUS_MAT3514_2026")
        self.base_courses = [
            {"course_code": "ABC", "credits": 2},
            *[{"course_code": f"MAT35{i:02d}", "credits": 2} for i in range(2, 10)],
            {"course_code": "HUS_MAT3514_2026", "credits": 2},
            {"course_code": "MAT3511", "credits": 2},
        ]  # 11 môn, mỗi môn 2 TC = 22 TC
        self.svc.seed_plan(
            self.uni,
            self.student_code,
            self.term_code,
            self.base_courses[:10],
            max_credits_per_term=24,
        )
        test_app = FastAPI(default_response_class=CleanJSONResponse)
        register_handlers(test_app)
        test_app.include_router(plan_undo.router, prefix=f"/{API_VERSION}")
        self.client = TestClient(test_app, raise_server_exceptions=False)

    def test_tc01_unit_bva_min_valid_remove_1_course_and_undo(self) -> None:
        """TC-01 [Unit/BVA]: Biên dưới hợp lệ N=1 (min), mã môn L=3 ('ABC', min) và dt=0.0s (min)."""
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            ["ABC"],
            actor_student_code=self.student_code,
        )
        self.assertEqual(res["removed_count"], 1)
        self.assertEqual(res["remaining_credits"], 18)

        undo_res = self.svc.undo_last_removal(
            self.uni,
            self.student_code,
            self.term_code,
            actor_student_code=self.student_code,
            undo_token=res["undo_token"],
        )
        self.assertEqual(undo_res["restored_codes"], ["ABC"])
        self.assertEqual(undo_res["total_credits"], 20)

    def test_tc02_unit_bva_max_valid_remove_10_courses_and_undo_at_exact_ttl_300s(self) -> None:
        """TC-02 [Unit/BVA]: Biên trên hợp lệ N=10 (max), mã môn L=16 ('HUS_MAT3514_2026', max) và dt=300.0s (max)."""
        codes_10 = [c["course_code"] for c in self.base_courses[:10]]
        self.assertEqual(len(codes_10[0]), 3)
        self.assertEqual(len(codes_10[-1]), 16)
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            codes_10,
            actor_student_code=self.student_code,
        )
        self.assertEqual(res["removed_count"], 10)
        self.assertEqual(res["remaining_credits"], 0)

        self.clock.advance(300.0)
        undo_res = self.svc.undo_last_removal(
            self.uni,
            self.student_code,
            self.term_code,
            actor_student_code=self.student_code,
            undo_token=res["undo_token"],
        )
        self.assertEqual(len(undo_res["restored_codes"]), 10)
        self.assertEqual(undo_res["total_credits"], 20)

    def test_tc03_unit_bva_negative_empty_course_list_n0(self) -> None:
        """TC-03 [Unit/BVA - Negative]: Biên dưới không hợp lệ N=0 (min-1, danh sách rỗng [])."""
        with self.assertRaises(PlanUndoValidationError):
            self.svc.remove_planned_courses(
                self.uni,
                self.student_code,
                self.term_code,
                [],
                actor_student_code=self.student_code,
            )
        self.assertEqual(self.svc.total_credits(self.uni, self.student_code, self.term_code), 20)
        self.assertEqual(len(self.svc._snapshots_by_token), 0)
        self.assertEqual(len(self.svc._latest_snapshot), 0)

    def test_tc04_unit_bva_negative_exceed_max_batch_n11(self) -> None:
        """TC-04 [Unit/BVA - Negative]: Ngay trên biên trên N=11 (max+1 > MAX_BATCH_REMOVE=10)."""
        self.svc.seed_plan(self.uni, self.student_code, self.term_code, self.base_courses)
        codes_11 = [c["course_code"] for c in self.base_courses]
        with self.assertRaises(PlanUndoValidationError):
            self.svc.remove_planned_courses(
                self.uni,
                self.student_code,
                self.term_code,
                codes_11,
                actor_student_code=self.student_code,
            )
        self.assertEqual(self.svc.total_credits(self.uni, self.student_code, self.term_code), 22)
        self.assertEqual(len(self.svc._snapshots_by_token), 0)
        self.assertEqual(len(self.svc._latest_snapshot), 0)

    def test_tc05_unit_bva_negative_whitespace_and_code_length_boundaries(self) -> None:
        """TC-05 [Unit/BVA - Negative]: Chuỗi rỗng '', khoảng trắng '   ' (L=0), L=2 (min-1) và L=17 (max+1)."""
        for invalid_code in ["", "   ", "IT", "HUS_MAT3514_EXTRA", "MAT$3514"]:
            with self.assertRaises(PlanUndoValidationError, msg=f"Did not reject {invalid_code!r}"):
                self.svc.remove_planned_courses(
                    self.uni,
                    self.student_code,
                    self.term_code,
                    [invalid_code],
                    actor_student_code=self.student_code,
                )
        for bad_token in ["tok12", "u" * 41]:
            with self.assertRaises(PlanUndoValidationError):
                self.svc.undo_last_removal(
                    self.uni,
                    self.student_code,
                    self.term_code,
                    actor_student_code=self.student_code,
                    undo_token=bad_token,
                )
        for bad_cr in [0, 25]:
            with self.assertRaises(PlanUndoValidationError):
                self.svc.seed_plan(
                    self.uni,
                    self.student_code,
                    self.term_code,
                    [{"course_code": "MAT3514", "credits": bad_cr}],
                )
        self.assertEqual(self.svc.total_credits(self.uni, self.student_code, self.term_code), 20)
        self.assertEqual(len(self.svc._snapshots_by_token), 0)
        self.assertEqual(len(self.svc._latest_snapshot), 0)

    def test_tc06_unit_bva_boundary_credit_exact_24_passes(self) -> None:
        """TC-06 [Unit/BVA]: Tổng tín chỉ sau khi Undo chạm đúng biên trên C_after = 24 TC (max)."""
        self.svc.seed_plan(
            self.uni,
            self.student_code,
            self.term_code,
            [{"course_code": "MAT3514", "credits": 1}, {"course_code": "MAT3502", "credits": 23}],
            max_credits_per_term=24,
        )
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            ["MAT3514"],
            actor_student_code=self.student_code,
        )
        self.assertEqual(res["remaining_credits"], 23)
        undo_res = self.svc.undo_last_removal(
            self.uni,
            self.student_code,
            self.term_code,
            actor_student_code=self.student_code,
            undo_token=res["undo_token"],
        )
        self.assertEqual(undo_res["total_credits"], 24)

    def test_tc07_unit_bva_failure_path_credit_25_exceeds_limit_and_rolls_back(self) -> None:
        """TC-07 [Unit/BVA - Failure Path]: C_after = 25 TC (max+1 > 24) -> Báo lỗi & bảo toàn 22 TC."""
        self.svc.seed_plan(
            self.uni,
            self.student_code,
            self.term_code,
            [{"course_code": "MAT3514", "credits": 3}, {"course_code": "MAT3502", "credits": 21}],
            max_credits_per_term=24,
        )
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            ["MAT3514"],
            actor_student_code=self.student_code,
        )
        # Ghi chú white-box setup: chèn trực tiếp vào _plans để giả lập thêm môn 1 TC vì slice chưa có API add_course
        key = (self.uni, self.student_code, self.term_code)
        self.svc._plans[key]["PES1001"] = self.svc._plans[key]["MAT3502"].__class__("PES1001", 1)
        with self.assertRaises(PlanUndoValidationError):
            self.svc.undo_last_removal(
                self.uni,
                self.student_code,
                self.term_code,
                actor_student_code=self.student_code,
                undo_token=res["undo_token"],
            )
        self.assertEqual(self.svc.total_credits(self.uni, self.student_code, self.term_code), 22)

    def test_tc08_unit_bva_negative_ttl_expired_at_300_1s(self) -> None:
        """TC-08 [Unit/BVA - Negative]: Ngay ngoài biên thời gian sống dt = 300.1s (max+0.1 > 300.0s)."""
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            ["ABC"],
            actor_student_code=self.student_code,
        )
        self.clock.advance(300.1)
        with self.assertRaises(PlanUndoConflictError):
            self.svc.undo_last_removal(
                self.uni,
                self.student_code,
                self.term_code,
                actor_student_code=self.student_code,
                undo_token=res["undo_token"],
            )
        self.assertEqual(self.svc.total_credits(self.uni, self.student_code, self.term_code), 18)

    def test_tc09_unit_failure_path_double_undo_idempotency(self) -> None:
        """TC-09 [Unit - Failure Path]: Gọi Undo lần thứ 2 trên cùng undo_token đã tiêu thụ -> 409 Conflict."""
        res = self.svc.remove_planned_courses(
            self.uni,
            self.student_code,
            self.term_code,
            ["ABC"],
            actor_student_code=self.student_code,
        )
        self.svc.undo_last_removal(
            self.uni,
            self.student_code,
            self.term_code,
            actor_student_code=self.student_code,
            undo_token=res["undo_token"],
        )
        with self.assertRaises(PlanUndoConflictError):
            self.svc.undo_last_removal(
                self.uni,
                self.student_code,
                self.term_code,
                actor_student_code=self.student_code,
                undo_token=res["undo_token"],
            )

    def test_tc10_api_integration_whitespace_course_code_rejected_422(self) -> None:
        """TC-10 [API/Integration - Negative]: Gửi course_codes chứa '   ' qua HTTP -> 422 validation_error."""
        undo_service._plans.clear()
        undo_service.seed_plan("HUS", "22001597", "20261", [{"course_code": "MAT3514", "credits": 3}])
        resp = self.client.post(
            "/v1/universities/HUS/students/22001597/plan/remove",
            json={"term": "20261", "course_codes": ["   "]},
            headers={"X-Actor-Student-Code": "22001597"},
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "validation_error")

    def test_tc11_api_quick_undo_without_token_rejects_unauthorized_actor(self) -> None:
        """TC-11 [API/Security - Path 1 Auth]: Gọi Quick-Undo (undo_token=None) bởi SV khác -> 403 Forbidden."""
        undo_service._plans.clear()
        undo_service._latest_snapshot.clear()
        undo_service._snapshots_by_token.clear()
        undo_service.seed_plan("HUS", "22001597", "20261", [{"course_code": "MAT3514", "credits": 3}])
        self.client.post(
            "/v1/universities/HUS/students/22001597/plan/remove",
            json={"term": "20261", "course_codes": ["MAT3514"]},
            headers={"X-Actor-Student-Code": "22001597"},
        )
        resp = self.client.post(
            "/v1/universities/HUS/students/22001597/plan/undo",
            json={"term": "20261", "undo_token": None},
            headers={"X-Actor-Student-Code": "22009999"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"]["code"], "forbidden_plan_access")

    def test_tc12_api_undo_by_explicit_token_rejects_cross_user_idor(self) -> None:
        """TC-12 [API/Security - Path 2 Auth]: SV khác dùng undo_token bị lộ -> 403 Forbidden."""
        undo_service._plans.clear()
        undo_service._latest_snapshot.clear()
        undo_service._snapshots_by_token.clear()
        undo_service.seed_plan("HUS", "22001597", "20261", [{"course_code": "MAT3514", "credits": 3}])

        rem_resp = self.client.post(
            "/v1/universities/HUS/students/22001597/plan/remove",
            json={"term": "20261", "course_codes": ["MAT3514"]},
            headers={"X-Actor-Student-Code": "22001597"},
        )
        self.assertEqual(rem_resp.status_code, 200)
        stolen_token = rem_resp.json()["undo_token"]

        # Kẻ tấn công (22009999) truyền trực tiếp stolen_token vào Đường đi 2 (Explicit Token)
        attack_resp = self.client.post(
            "/v1/universities/HUS/students/22001597/plan/undo",
            json={"term": "20261", "undo_token": stolen_token},
            headers={"X-Actor-Student-Code": "22009999"},
        )
        self.assertEqual(attack_resp.status_code, 403)
        self.assertEqual(attack_resp.json()["error"]["code"], "forbidden_plan_access")

        # Đảm bảo token của chủ sở hữu thật vẫn chưa bị tiêu thụ (consumed=False)
        owner_resp = self.client.post(
            "/v1/universities/HUS/students/22001597/plan/undo",
            json={"term": "20261", "undo_token": stolen_token},
            headers={"X-Actor-Student-Code": "22001597"},
        )
        self.assertEqual(owner_resp.status_code, 200)
        self.assertEqual(owner_resp.json()["total_credits"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
