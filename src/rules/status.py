"""Các quy tắc xác định trạng thái học phần trong chương trình đào tạo."""

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd


def elective_credits_passed(courses: pd.DataFrame, passed: Iterable[str]) -> dict[str, int]:
    """Tính tổng tín chỉ đạt được trong từng khối tự chọn."""
    passed_codes = set(passed)
    elective_courses = courses[courses["elective_block"].notna()]
    earned = elective_courses[elective_courses["course_code"].isin(passed_codes)]
    totals = earned.groupby("elective_block")["credits"].sum()
    return {
        str(block_code): int(totals.get(block_code, 0))
        for block_code in elective_courses["elective_block"].drop_duplicates()
    }


def fits_in_block(credits: int, taken: int, required: int) -> bool:
    """Cho biết số tín chỉ mới có nằm trong giới hạn của khối hay không."""
    return taken + credits <= required


def _status_data(
    repo: Any, student: pd.Series | Mapping[str, Any]
) -> tuple[pd.DataFrame, dict[str, str], dict[str, dict[str, Any]]]:
    """Tính trạng thái cơ sở và thông tin khối tự chọn dùng chung."""
    curriculum_code = student["curriculum_code"]
    courses = repo.curriculum_courses(curriculum_code)
    passed = set(student["passed_courses"])
    outstanding = set(student["outstanding_courses"])
    statuses = {code: "eligible" for code in courses["course_code"]}

    earned_by_block = elective_credits_passed(courses, passed)
    blocks = repo.elective_blocks(curriculum_code)
    block_details: dict[str, dict[str, Any]] = {}
    for _, block in blocks.iterrows():
        block_code = block["block_code"]
        required = int(block["required_credits"])
        earned = earned_by_block.get(str(block_code), 0)
        block_details[str(block_code)] = {
            "block_code": block_code,
            "block_name": block["block_name"],
            "required_credits": required,
            "earned_credits": earned,
        }
        if earned >= required:
            in_block = courses[courses["elective_block"] == block_code]
            for code in in_block["course_code"]:
                if code not in passed:
                    statuses[code] = "block_complete"

    for _, course in courses.iterrows():
        code = course["course_code"]
        if code in passed:
            statuses[code] = "passed"
            continue
        if statuses[code] == "block_complete":
            continue
        groups = course["prerequisite_groups"]
        if any(not (set(group) & passed) for group in groups):
            statuses[code] = "missing_prerequisite"
        elif code in outstanding:
            statuses[code] = "retake"
    return courses, statuses, block_details


def course_status_details(repo: Any, student: pd.Series | Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Trả trạng thái và thông tin giải thích cho từng học phần trong khung."""
    courses, statuses, blocks = _status_data(repo, student)
    passed = set(student["passed_courses"])
    results = pd.DataFrame()
    student_id = student.get("student_id")
    if student_id is not None:
        results = repo.course_results(student_id)
        if not results.empty and "recency" in results:
            results = results[results["recency"] == 1]
        elif not results.empty:
            # Khi không có cột recency, chọn lần mới nhất theo học kỳ và số lần học.
            results = results.sort_values(["term_code", "attempt_no"]).drop_duplicates("course_code", keep="last")
    latest = results.set_index("course_code").to_dict("index") if not results.empty else {}

    details: dict[str, dict[str, Any]] = {}
    for _, course in courses.iterrows():
        code = course["course_code"]
        status = statuses[code]
        item: dict[str, Any] = {"status": status}
        if status == "missing_prerequisite":
            item["missing_prerequisites"] = [
                list(group) for group in course["prerequisite_groups"] if not (set(group) & passed)
            ]
        elif status == "block_complete":
            block_code = course["elective_block"]
            item["block"] = blocks[str(block_code)]
        elif status in {"passed", "retake"} and code in latest:
            result = latest[code]
            item["last_attempt"] = {
                "term_code": result["term_code"],
                "attempt_no": int(result["attempt_no"]),
                "score": None if result["status"] == "exempted" else result["score"],
                "letter_grade": None if result["status"] == "exempted" else result["letter_grade"],
            }
        details[code] = item
    return details


def course_status(repo: Any, student: pd.Series | Mapping[str, Any]) -> dict[str, str]:
    """Trả mã trạng thái của từng học phần trong chương trình đào tạo."""
    return {code: detail["status"] for code, detail in course_status_details(repo, student).items()}
