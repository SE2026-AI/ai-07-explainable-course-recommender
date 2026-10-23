"""What-if của hợp đồng mục 6.6: "nếu tôi đạt / trượt môn này", "nếu tôi chưa học môn này kỳ này", "nếu tôi
đổi môn này lấy môn khác" thì gợi ý đổi ra sao.

Giả định được áp lên một BẢN SAO của dòng sinh viên trong bộ nhớ và KHÔNG ĐƯỢC ghi vào cơ sở dữ liệu.
Tầng này KHÔNG đọc database: mọi thứ cần tra từ khung được truyền vào, nên `test/test_whatif.py` chạy
được mà không cần PostgreSQL.
"""
from collections.abc import Collection, Mapping, Sequence

import pandas as pd

ASSUMPTION_STATUSES = ("passed", "failed")
ASSUMPTION_KEYS = {"course_code", "status", "score"}
SWAP_KEYS = {"course_code", "replacement"}


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


def check_choices(skip: Sequence[str], swap: Sequence[Mapping], statuses: Mapping[str, str],
                  recommendable: Collection[str], k: int) -> tuple[set[str], dict[str, int]]:
    """Kiểm tra hai lựa chọn của sinh viên cho học kỳ đang gợi ý: `skip` là các môn chưa muốn học kỳ này,
    `swap` là các cặp `{"course_code", "replacement"}` đổi một môn lấy môn khác.

    Trả về `(removed, chosen)`. `removed` là mọi môn phải vắng mặt trong `items`: các mã của `skip` và mọi
    `swap[].course_code`. `chosen` ánh xạ mỗi `replacement` tới vị trí của nó trong `swap`, để khi môn đó không
    xếp được vào khối tự chọn thì lỗi chỉ đúng trường.

    `statuses` là trạng thái SAU khi áp `assumptions`. Hai lựa chọn này chỉ đổi môn nào vào `items`, không đổi
    trạng thái học phần, nên mọi mã phải đang có trạng thái trong `recommendable`: bỏ một môn vốn không được
    gợi ý là vô nghĩa, còn chọn thay một môn chưa đủ điều kiện là phá ràng buộc cứng (mục 6.6, quy định 1).
    Mỗi mã chỉ xuất hiện một lần trong cả hai danh sách, và số môn chọn thay không vượt `k`. Sai thì raise
    `ValueError`, thông điệp mở đầu bằng đường dẫn tới trường sai như `apply_assumptions()`."""
    used = set()

    def claim(code, where):
        if not isinstance(code, str) or code not in statuses:
            raise ValueError(f"{where}: {code!r} không thuộc khung của sinh viên")
        if statuses[code] not in recommendable:
            raise ValueError(f"{where}: {code} không gợi ý được ở học kỳ này (trạng thái {statuses[code]})")
        if code in used:
            raise ValueError(f"{where}: {code} đã có ở phía trên trong skip hoặc swap")
        used.add(code)

    removed, chosen = set(), {}
    for index, code in enumerate(skip):
        claim(code, f"skip[{index}]")
        removed.add(code)
    for index, pair in enumerate(swap):
        where = f"swap[{index}]"
        if not isinstance(pair, Mapping):
            raise ValueError(f"{where}: phải là object có course_code và replacement")
        unknown = sorted(set(pair) - SWAP_KEYS)
        if unknown:
            raise ValueError(f"{where}: khóa không có trong hợp đồng: {', '.join(unknown)}")
        claim(pair.get("course_code"), f"{where}.course_code")
        claim(pair.get("replacement"), f"{where}.replacement")
        removed.add(pair["course_code"])
        chosen[pair["replacement"]] = index
    if len(chosen) > k:
        raise ValueError(f"swap: {len(chosen)} môn chọn thay, nhiều hơn limit = {k}")
    return removed, chosen
