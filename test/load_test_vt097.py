"""
Kịch bản kiểm chứng tải 60 người dùng/tác vụ đồng thời (p95 <= 2.0s) và kiểm tra Race Condition 20 luồng
cho biến thể VT-097 (Phạm Hữu Hưng - 22001597) trên dự án AI-07.
Báo cáo cả 2 chế độ:
1. Chế độ có giả lập độ trễ xếp hàng kết nối DB I/O (simulate_db_io_ms=18.0, QueuePool=15).
2. Chế độ không sleep (simulate_db_io_ms=0.0) đo overhead thực tế của ASGI TestClient và PlanUndoService.
"""
from __future__ import annotations

import json
import math
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routers.plan_undo import undo_service
from src.rules.plan_undo import PlanUndoConflictError

SEED = 22001597


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil((pct / 100.0) * len(sorted_vals)) - 1))
    return sorted_vals[idx]


def run_60_concurrent_tasks(simulate_db_io_ms: float = 18.0) -> dict[str, Any]:
    random.seed(SEED)
    undo_service._plans.clear()
    undo_service._latest_snapshot.clear()
    undo_service._snapshots_by_token.clear()

    num_users = 60
    for idx in range(num_users):
        sid = f"2200{1500 + idx:04d}"
        undo_service.seed_plan(
            "HUS",
            sid,
            "20261",
            [
                {"course_code": "MAT3514", "credits": 3},
                {"course_code": "INT3405", "credits": 3},
                {"course_code": "INT3406", "credits": 3},
            ],
            max_credits_per_term=24,
        )

    clients = [TestClient(app, raise_server_exceptions=False) for _ in range(num_users)]

    def worker_task(idx: int) -> tuple[bool, float]:
        sid = f"2200{1500 + idx:04d}"
        client = clients[idx]
        t0 = time.perf_counter()
        if simulate_db_io_ms > 0.0:
            batch_wave = idx // 15
            time.sleep((simulate_db_io_ms / 1000.0) * (1.0 + 1.8 * batch_wave))
        r1 = client.post(
            f"/v1/universities/HUS/students/{sid}/plan/remove",
            json={"term": "20261", "course_codes": ["MAT3514", "INT3405"]},
            headers={"X-Actor-Student-Code": sid},
        )
        if r1.status_code != 200:
            return False, time.perf_counter() - t0
        token = r1.json()["undo_token"]
        if simulate_db_io_ms > 0.0:
            time.sleep(simulate_db_io_ms / 1000.0)
        r2 = client.post(
            f"/v1/universities/HUS/students/{sid}/plan/undo",
            json={"term": "20261", "undo_token": token},
            headers={"X-Actor-Student-Code": sid},
        )
        ok = r2.status_code == 200 and r2.json().get("total_credits") == 9
        return ok, time.perf_counter() - t0

    t_wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_users) as pool:
        results = list(pool.map(worker_task, range(num_users)))
    wall_time = time.perf_counter() - t_wall_start

    latencies = sorted(lat for _, lat in results)
    success_count = sum(1 for ok, _ in results if ok)
    p95 = percentile(latencies, 95)
    return {
        "simulate_db_io_ms": simulate_db_io_ms,
        "concurrent_users": num_users,
        "success_count": success_count,
        "error_rate_pct": round((num_users - success_count) * 100.0 / num_users, 2),
        "wall_time_s": round(wall_time, 4),
        "throughput_tasks_per_s": round(num_users / wall_time, 2),
        "min_s": round(latencies[0], 4),
        "mean_s": round(statistics.mean(latencies), 4),
        "p50_s": round(percentile(latencies, 50), 4),
        "p90_s": round(percentile(latencies, 90), 4),
        "p95_s": round(p95, 4),
        "p99_s": round(percentile(latencies, 99), 4),
        "max_s": round(latencies[-1], 4),
        "target_p95_s": 2.0,
        "meets_p95_target": p95 <= 2.0,
    }


def run_60_direct_service_no_sleep() -> dict[str, Any]:
    random.seed(SEED)
    undo_service._plans.clear()
    undo_service._latest_snapshot.clear()
    undo_service._snapshots_by_token.clear()
    num_users = 60
    for idx in range(num_users):
        sid = f"2200{1500 + idx:04d}"
        undo_service.seed_plan(
            "HUS",
            sid,
            "20261",
            [
                {"course_code": "MAT3514", "credits": 3},
                {"course_code": "INT3405", "credits": 3},
                {"course_code": "INT3406", "credits": 3},
            ],
            max_credits_per_term=24,
        )

    def direct_worker(idx: int) -> tuple[bool, float]:
        sid = f"2200{1500 + idx:04d}"
        t0 = time.perf_counter()
        rem = undo_service.remove_planned_courses(
            "HUS", sid, "20261", ["MAT3514", "INT3405"], actor_student_code=sid
        )
        res = undo_service.undo_last_removal(
            "HUS", sid, "20261", actor_student_code=sid, undo_token=rem["undo_token"]
        )
        return res["total_credits"] == 9, time.perf_counter() - t0

    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_users) as pool:
        results = list(pool.map(direct_worker, range(num_users)))
    wall = time.perf_counter() - t_start
    latencies = sorted(lat for _, lat in results)
    return {
        "concurrent_users": num_users,
        "success_count": sum(1 for ok, _ in results if ok),
        "wall_time_s": round(wall, 4),
        "min_s": round(latencies[0], 4),
        "mean_s": round(statistics.mean(latencies), 4),
        "p50_s": round(percentile(latencies, 50), 4),
        "p95_s": round(percentile(latencies, 95), 4),
        "max_s": round(latencies[-1], 4),
    }


def run_race_condition_20_threads() -> dict[str, int]:
    undo_service._plans.clear()
    undo_service._latest_snapshot.clear()
    undo_service._snapshots_by_token.clear()
    undo_service.seed_plan("HUS", "22001597", "20261", [{"course_code": "MAT3514", "credits": 3}])
    rem = undo_service.remove_planned_courses(
        "HUS", "22001597", "20261", ["MAT3514"], actor_student_code="22001597"
    )
    token = rem["undo_token"]

    def attempt_undo(_: int) -> str:
        try:
            undo_service.undo_last_removal(
                "HUS",
                "22001597",
                "20261",
                actor_student_code="22001597",
                undo_token=token,
            )
            return "SUCCESS"
        except PlanUndoConflictError:
            return "CONFLICT_409"

    with ThreadPoolExecutor(max_workers=20) as pool:
        outcomes = list(pool.map(attempt_undo, range(20)))
    return {
        "SUCCESS": outcomes.count("SUCCESS"),
        "CONFLICT_409": outcomes.count("CONFLICT_409"),
    }


if __name__ == "__main__":
    mode_with_sleep = run_60_concurrent_tasks(simulate_db_io_ms=18.0)
    mode_no_sleep = run_60_concurrent_tasks(simulate_db_io_ms=0.0)
    mode_direct = run_60_direct_service_no_sleep()
    race = run_race_condition_20_threads()
    report = {
        "seed": SEED,
        "mode_simulated_io_18ms": mode_with_sleep,
        "mode_no_sleep_pure_overhead": mode_no_sleep,
        "mode_no_sleep_direct_service": mode_direct,
        "race_20_threads_on_1_token": race,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
