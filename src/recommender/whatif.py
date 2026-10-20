"""Giả định what-if: "nếu tôi đạt / trượt môn này thì gợi ý đổi ra sao" (hợp đồng mục 6.6).

Giả định được áp lên một BẢN SAO của dòng sinh viên trong bộ nhớ và KHÔNG ĐƯỢC ghi vào cơ sở dữ liệu.
Tầng này KHÔNG đọc database: mọi thứ cần tra từ khung được truyền vào, nên `test/test_whatif.py` chạy
được mà không cần PostgreSQL.
"""
from collections.abc import Collection, Mapping, Sequence

import pandas as pd

ASSUMPTION_STATUSES = ("passed", "failed")
ASSUMPTION_KEYS = {"course_code", "status", "score"}


def apply_assumptions(student: pd.Series, assumptions: Sequence[Mapping], course_codes: Collection[str],
                      max_score: float, attempt_term: str) -> pd.Series:
    """Bản sao của `student` (một dòng của `repo.student()`) với các kết quả giả định đã áp vào.

    Mỗi giả định là `{"course_code", "status": "passed" | "failed", "score" (tùy chọn)}`, và được coi là lần
    học mới nhất của môn đó, diễn ra ở `attempt_term` — học kỳ ngay trước học kỳ đang gợi ý. Bản sao đổi
    đúng những cột mà tầng luật và tầng xếp hạng đọc: `passed_courses`, `outstanding_courses`,
    `latest_scores`, `latest_attempts`. Tín chỉ và GPA KHÔNG đổi, nên đừng dùng bản sao để dựng `profile`.

    Giả định sai làm hàm raise `ValueError`, thông điệp mở đầu bằng đường dẫn tới trường sai (ví dụ
    `assumptions[1].score`) để tầng API đưa vào `details.fields` của `validation_error` (mục 5)."""
    view = student.copy()
    passed, outstanding = set(view["passed_courses"]), set(view["outstanding_courses"])
    scores, attempts = dict(view["latest_scores"]), dict(view["latest_attempts"])
    seen = set()
    for index, assumption in enumerate(assumptions):
        where = f"assumptions[{index}]"
        unknown = sorted(set(assumption) - ASSUMPTION_KEYS)
        if unknown:
            raise ValueError(f"{where}: khóa không có trong hợp đồng: {', '.join(unknown)}")
        code, status, score = assumption.get("course_code"), assumption.get("status"), assumption.get("score")
        if code not in course_codes:
            raise ValueError(f"{where}.course_code: {code!r} không thuộc khung của sinh viên")
        if code in seen:
            raise ValueError(f"{where}.course_code: {code} đã có giả định ở phía trên")
        if status not in ASSUMPTION_STATUSES:
            raise ValueError(f"{where}.status: chỉ nhận {' hoặc '.join(ASSUMPTION_STATUSES)}, nhận được {status!r}")
        if score is not None and (isinstance(score, bool) or not isinstance(score, int | float)
                                  or not 0 <= score <= float(max_score)):
            raise ValueError(f"{where}.score: phải là số trong [0, {float(max_score):g}], nhận được {score!r}")
        seen.add(code)

        previous = attempts.get(code)
        attempts[code] = {"term_code": str(attempt_term),
                          "attempt_no": (previous["attempt_no"] + 1) if previous else 1,
                          "score": None if score is None else float(score),
                          "letter_grade": None, "status": status}
        if score is None:
            scores.pop(code, None)
        else:
            scores[code] = float(score)
        if status == "passed":
            passed.add(code)
            outstanding.discard(code)
        else:
            passed.discard(code)
            outstanding.add(code)

    view["passed_courses"] = sorted(passed)
    view["outstanding_courses"] = sorted(outstanding)
    view["latest_scores"] = scores
    view["latest_attempts"] = attempts
    return view
