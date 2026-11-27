"""Tầng xếp hạng: chọn học phần nên học ở học kỳ tới và giải thích vì sao.

Hàm công bố cho tầng API (mục 6.6, 6.11) và cho `test/test_recommender_contract.py`:

    recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None,
              min_credits=None, max_credits=None, include=None) -> dict

`student` là một dòng của `repo.student()` hoặc `repo.students()`, hoặc dòng cùng dạng mà tầng luật dựng từ
bảng điểm sinh viên tự nhập (mục 6.10). Trạng thái học phần do `src/rules/status.py` quyết định; tầng này
chỉ xếp hạng trong số học phần đã được phép gợi ý. Công thức của sáu tiêu chí: `docs/architecture/ranking.md`.
"""
from copy import deepcopy
from numbers import Integral

import pandas as pd

from src.explain import credit_window_text, not_selected_text, status_text, warning_text
from src.recommender.scoring import (
    DEFAULT_WEIGHTS,
    interest,
    merge_weights,
    outstanding_retake,
    schedule,
    sort_reasons,
    strong_topic,
    target_semester,
    total_score,
    unlocks,
)
from src.recommender.selection import pick_items, pick_within_credits
from src.recommender.whatif import apply_assumptions, check_choices, check_window_choices
from src.rules.plan import term_credits
from src.rules.status import course_status_details, elective_credits_passed

# Tầng API đọc hai hằng số này cho GET /v1/meta (mục 6.1).
ALGORITHM = "rule_based_weighted"
ALGORITHM_VERSION = "1.1.0"

# Chỉ hai trạng thái này được vào danh sách gợi ý (mục 6.6, quy định 1).
RECOMMENDABLE_STATUSES = ("retake", "eligible")

# Học phần khung không ghi kỳ dự kiến thì xếp sau cùng khi hai học phần bằng điểm (mục 3.3).
MISSING_SEMESTER = 10**6

# Khoảng tín chỉ của mục 6.11. Mức sàn 10 là của sản phẩm; mức trần là `max_credits_per_term` của từng khung.
MIN_CREDITS_FLOOR = 10
DEFAULT_MIN_CREDITS = 10
DEFAULT_MAX_CREDITS = 20

__all__ = ["ALGORITHM", "ALGORITHM_VERSION", "DEFAULT_MAX_CREDITS", "DEFAULT_MIN_CREDITS", "DEFAULT_WEIGHTS",
           "MIN_CREDITS_FLOOR", "recommend"]


def _recommended_semester(course):
    """Kỳ dự kiến của một học phần trong khung, `None` khi khung không ghi."""
    value = getattr(course, "recommended_semester", None)
    return None if value is None or pd.isna(value) else int(value)


def _semester_key(course):
    """Khóa sắp xếp theo kỳ dự kiến; học phần không ghi kỳ xếp sau cùng (mục 3.3)."""
    semester = _recommended_semester(course)
    return MISSING_SEMESTER if semester is None else semester


def _attempt_term(repo, university_code, term_code):
    """Học kỳ chính (không phải kỳ hè) ngay trước `term_code`: nơi một giả định what-if "diễn ra".

    Giả định nói về môn sinh viên đang học dở hoặc chưa có điểm, nên lần học giả định thuộc học kỳ vừa
    qua. v1 không gợi ý cho kỳ hè (ranking.md mục 3.2), nên kỳ hè bị bỏ qua."""
    terms = repo.terms(university_code)
    earlier = terms[(terms["term_code"] < term_code) & terms["term_no"].isin([1, 2])]["term_code"]
    return str(earlier.max()) if not earlier.empty else str(term_code)


def _strong_topics(repo, courses, attempts):
    """Chủ đề sinh viên đang học tốt: mã chủ đề → dict sẵn sàng cho `scoring.strong_topic`.

    Tính trên lần học gần nhất của mọi học phần CÓ ĐIỂM, kể cả môn chưa đạt: điểm đo năng lực ở
    chủ đề, không đo chuyện đã qua môn hay chưa. Môn được miễn không có điểm nên không tính."""
    topic_names = repo.topics().set_index("topic_code")["topic_name"].to_dict()
    scores_by_topic = {}
    for course in courses.itertuples():
        topic, attempt = course.primary_topic, attempts.get(course.course_code)
        if not isinstance(topic, str) or not attempt or attempt["score"] is None:
            continue
        scores_by_topic.setdefault(topic, []).append((course.course_code, attempt["score"]))
    return {topic: {"topic_code": topic,
                    "topic_name": str(topic_names.get(topic, topic)),
                    "average_score": sum(score for _, score in studied) / len(studied),
                    "course_codes": sorted(code for code, _ in studied)}
            for topic, studied in scores_by_topic.items()}


def _declared_topics(repo, student):
    """Chủ đề sinh viên tự khai: mã chủ đề → dict sẵn sàng cho `scoring.interest`.

    Sinh viên tự nhập bảng điểm không có `student_id` và v1 chưa nhận sở thích của họ, nên không có chủ đề
    nào. Phải dừng ở đây: `repo.student_interests(None)` trả về sở thích của MỌI sinh viên."""
    student_id = student.get("student_id")
    if student_id is None or pd.isna(student_id):
        return {}
    declared = repo.student_interests(student_id)
    return {row.topic_code: {"topic_code": str(row.topic_code),
                             "topic_name": str(row.topic_name),
                             "weight": float(row.weight)}
            for row in declared.itertuples()}


def _elective_progress(courses, student):
    """Tín chỉ đã đạt và các môn chưa đạt của từng khối tự chọn: `(taken, open_courses)` cho `pick_items`.

    Tín chỉ đã đạt lấy từ `rules.elective_credits_passed()`, chính phép tính quyết định trạng thái
    `block_complete`, nên khối mà tầng luật coi là đủ thì ở đây cũng đủ."""
    passed = set(student["passed_courses"])
    open_courses = {}
    for course in courses.itertuples():
        if isinstance(course.elective_block, str) and course.course_code not in passed:
            open_courses.setdefault(course.elective_block, {})[course.course_code] = int(course.credits)
    return elective_credits_passed(courses, passed), open_courses


def _not_eligible(courses, details):
    """Mọi học phần không gợi ý được, mỗi dòng cùng dạng một dòng `courses` của mục 6.5: thông tin môn,
    `status` kèm chi tiết của tầng luật, rồi câu `text` của tầng giải thích. Sắp theo `course_code` (mục 3.3).

    Chép sâu chi tiết của tầng luật: các môn cùng khối dùng chung một dict `block`, nên sửa một dòng của
    phản hồi không được làm đổi dòng khác."""
    names = dict(zip(courses["course_code"], courses["course_name"], strict=True))
    rows = []
    for course in courses.sort_values("course_code").to_dict("records"):
        detail = details[course["course_code"]]
        if detail["status"] in RECOMMENDABLE_STATUSES:
            continue
        rows.append({"course_code": str(course["course_code"]),
                     "course_name": str(course["course_name"]),
                     "credits": int(course["credits"]),
                     "block_code": str(course["block_code"]),
                     **deepcopy(detail),
                     "text": status_text(course, detail, names)})
    return rows


def _require_chosen(items, chosen, ranked):
    """Môn chọn thay chỉ vắng mặt khi nó làm khối tự chọn không còn hoàn thành đúng được, cùng các môn chọn
    thay khác: luật khối là ràng buộc cứng (mục 6.6, quy định 1), nên đó là lựa chọn sai, không lặng lẽ bỏ."""
    picked = {item["course_code"] for item in items}
    blocks = {item["course_code"]: block for item, block in ranked}
    for code, index in sorted(chosen.items(), key=lambda pair: pair[1]):
        if code not in picked:
            raise ValueError(f"swap[{index}].replacement: {code} làm khối tự chọn {blocks[code]} không còn "
                             "hoàn thành đúng số tín chỉ được, cùng các môn đã chọn")


def _student_semester(student, term):
    """Vị trí của sinh viên trong lộ trình của khung (mục 3.1). Dòng dựng từ bảng điểm tự nhập mang sẵn
    `target_semester` = số kỳ đã học + 1 (mục 6.10); dòng đọc từ cơ sở dữ liệu thì tính từ năm học và học kỳ."""
    value = student.get("target_semester")
    if value is not None and not pd.isna(value):
        return int(value)
    return target_semester(student["year_of_study"], term["term_no"])


def _credit_window(min_credits, max_credits, cap):
    """`(min, max)` của khoảng tín chỉ (mục 6.11), hoặc `None` khi người gọi không gửi cả hai, tức chọn theo `k`.

    Gửi một đầu thì đầu kia lấy mặc định: `max_credits` mặc định là `max(DEFAULT_MAX_CREDITS, min_credits)` nhưng
    không vượt trần, vì khung DEMO chỉ cho 12 tín chỉ một kỳ. Sàn là `MIN_CREDITS_FLOOR`, trần là
    `max_credits_per_term` của khung; sai thì `ValueError` mở đầu bằng tên trường sai, để tầng API đưa vào
    `details.fields`. Lỗi luôn chỉ vào trường người gọi đã gửi, không chỉ vào giá trị mặc định."""
    if min_credits is None and max_credits is None:
        return None
    low = DEFAULT_MIN_CREDITS if min_credits is None else min_credits
    for name, value in (("min_credits", low), ("max_credits", max_credits)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, Integral)):
            raise ValueError(f"{name}: phải là số nguyên, nhận được {value!r}")
    low = int(low)
    high = min(max(DEFAULT_MAX_CREDITS, low), cap) if max_credits is None else int(max_credits)
    if low < MIN_CREDITS_FLOOR:
        raise ValueError(f"min_credits: phải từ {MIN_CREDITS_FLOOR} tín chỉ trở lên, nhận được {low}")
    if low > cap:
        raise ValueError(f"min_credits: không được vượt {cap} tín chỉ, mức tối đa một học kỳ của khung, "
                         f"nhận được {low}")
    if high > cap:
        raise ValueError(f"max_credits: không được vượt {cap} tín chỉ, mức tối đa một học kỳ của khung, "
                         f"nhận được {high}")
    if low > high:
        raise ValueError(f"min_credits: phải nhỏ hơn hoặc bằng max_credits, nhận được {low} > {high}")
    return low, high


def _require_included(left_out, chosen, max_credits):
    """Môn sinh viên muốn học (`include`) chỉ vắng mặt khi chính lựa chọn đó sai: làm hỏng khối tự chọn, hoặc
    các môn muốn học cộng lại vượt `max_credits`. Báo lỗi đúng trường, không lặng lẽ bỏ (mục 6.11)."""
    refused = {item["course_code"]: (reason, data) for item, reason, data in left_out}
    for code, index in sorted(chosen.items(), key=lambda pair: pair[1]):
        if code not in refused:
            continue
        reason, data = refused[code]
        if reason == "block_full":
            raise ValueError(f"include[{index}]: {code} làm khối tự chọn {data['block_code']} không còn hoàn thành "
                             "đúng số tín chỉ được, cùng các môn muốn học khác")
        raise ValueError(f"include[{index}]: các môn muốn học cộng lại vượt max_credits = {max_credits} tín chỉ")


def _not_selected(left_out, block_names):
    """Mọi học phần học được mà không được xếp (mục 6.11), theo thứ tự xếp hạng, mỗi dòng kèm lý do và câu."""
    rows = []
    for item, reason, data in left_out:
        if reason == "block_full":
            data = {"block_code": data["block_code"], "block_name": block_names.get(data["block_code"]),
                    **{key: data[key] for key in ("required_credits", "taken_credits", "credits")}}
        rows.append({**{key: item[key] for key in ("course_code", "course_name", "credits", "block_code",
                                                    "status", "score")},
                     "reason": reason,
                     "text": not_selected_text(item, reason, data),
                     "data": data})
    return rows


def _warnings(student, window, total, names):
    """Cảnh báo của bảng điểm (do tầng luật đưa vào dòng sinh viên) rồi cảnh báo của chính lượt gợi ý (mục 4.7)."""
    raw = list(student.get("warnings") or [])
    low, _ = window
    if total < low:
        raw.append({"code": "below_min_credits", "data": {"min_credits": low, "total_credits": total}})
    rows = []
    for warning in raw:
        row = {"code": warning["code"]}
        if warning.get("course_code") is not None:
            row["course_code"] = warning["course_code"]
        rows.append({**row, "text": warning_text(warning, names), "data": dict(warning.get("data", {}))})
    return rows


def recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None,
              min_credits=None, max_credits=None, include=None):
    """Học phần nên học ở học kỳ `term_code`, mỗi phần tử kèm điểm và lời giải thích (mục 6.6).

    `student` phải được đọc ở cùng học kỳ, tức `repo.student(uni, code, term_code)`: `year_of_study` và
    các môn đã đạt đều tính theo mốc đó (mục 3.1). `term_code` để `None` là học kỳ cần gợi ý.

    `k` là số phần tử tối đa. `weights` gửi một phần được: khóa thiếu lấy mặc định. `assumptions` là các
    giả định what-if, áp lên bản sao trong bộ nhớ, không ghi database. `skip` là mã các môn sinh viên chưa
    muốn học kỳ này; `swap` là các cặp `{"course_code", "replacement"}` đổi một môn lấy môn khác — môn bị bỏ
    nhường chỗ cho môn xếp sau, môn chọn thay luôn có mặt nhưng vẫn sắp theo điểm (`whatif.check_choices`).
    Khóa trọng số lạ, trọng số âm, giả định hay lựa chọn sai làm hàm raise `ValueError`, để tầng API trả
    `validation_error` (mục 5).

    Trả về dict theo đúng thứ tự khóa của mục 6.6: `what_if`, `weights` (bảng đã ghép), `candidate_count`
    (mọi học phần `retake` + `eligible`, kể cả phần vượt `k`), `items` (đã sắp theo mục 3.3, mỗi phần tử có
    `rank`, `course_code`, `course_name`, `credits`, `block_code`, `status`, `score`, `reasons`),
    `not_eligible` (mọi học phần còn lại của khung: `passed`, `block_complete`, `missing_prerequisite`).

    Gửi `min_credits` hoặc `max_credits` thì chọn theo khoảng tín chỉ của mục 6.11 thay cho `k`: đi từ trên
    xuống, nhận môn khi tổng tín chỉ vẫn trong `max_credits` (`selection.pick_within_credits`). Khi đó
    `include` là các môn muốn học chắc chắn, xét trước mọi môn khác; `swap` không dùng được (đổi môn chính là
    `skip` cộng `include`). Phản hồi theo thứ tự khóa của mục 6.11: `what_if`, `weights`, `target_semester`,
    `credit_window`, `candidate_count`, `items`, `not_selected` (môn học được mà không được xếp, kèm lý do),
    `not_eligible`, `warnings`.
    """
    weights = merge_weights(weights)
    curriculum_code = student["curriculum_code"]
    courses = repo.curriculum_courses(curriculum_code)
    grading = repo.curriculum(curriculum_code)
    window = _credit_window(min_credits, max_credits, int(grading["max_credits_per_term"]))
    if window is None and include:
        raise ValueError("include: chỉ dùng cùng min_credits và max_credits (mục 6.11)")
    if window is not None and swap:
        raise ValueError("swap: không dùng cùng khoảng tín chỉ, hãy dùng skip và include (mục 6.11)")
    term = repo.term(student["university_code"], term_code or repo.setting("target_term_code"))
    if assumptions:
        student = apply_assumptions(student, assumptions, set(courses["course_code"]), grading["max_score"],
                                    _attempt_term(repo, student["university_code"], term["term_code"]))
    details = course_status_details(repo, student)
    statuses = {code: detail["status"] for code, detail in details.items()}
    if window is None:
        removed, chosen = check_choices(skip or [], swap or [], statuses, RECOMMENDABLE_STATUSES, k)
    else:
        # Môn trong `skip` vẫn được xếp hạng để `not_selected` giữ đúng thứ tự; chỉ bước chọn bỏ chúng qua.
        removed = set()
        skipped, chosen = check_window_choices(skip or [], include or [], statuses, RECOMMENDABLE_STATUSES)
    semester_no = _student_semester(student, term)
    prerequisites = dict(zip(courses["course_code"], courses["prerequisite_groups"], strict=True))
    attempts = student["latest_attempts"]
    strong = _strong_topics(repo, courses, attempts)
    declared = _declared_topics(repo, student)

    candidates = []
    for course in courses.itertuples():
        state = statuses.get(course.course_code)
        if state not in RECOMMENDABLE_STATUSES or course.course_code in removed:
            continue
        topic = course.primary_topic if isinstance(course.primary_topic, str) else None
        reasons = sort_reasons([
            outstanding_retake(attempts.get(course.course_code) if state == "retake" else None, weights),
            schedule(_recommended_semester(course), semester_no, weights),
            unlocks(course.course_code, prerequisites, weights),
            strong_topic(strong.get(topic), grading["pass_score"], grading["max_score"], weights),
            interest(declared.get(topic), weights),
        ])
        # `rank` đặt trước để thứ tự khóa của dict khớp ví dụ phản hồi ở mục 6.6; điền sau khi sắp.
        candidates.append(({"rank": None,
                            "course_code": str(course.course_code),
                            "course_name": str(course.course_name),
                            "credits": int(course.credits),
                            "block_code": str(course.block_code),
                            "status": state,
                            "score": total_score(reasons),
                            "reasons": reasons}, course))

    candidates.sort(key=lambda pair: (-pair[0]["score"], _semester_key(pair[1]),
                                      pair[0]["course_code"]))

    blocks = repo.elective_blocks(curriculum_code).set_index("block_code")
    required = blocks["required_credits"].to_dict()
    taken, open_courses = _elective_progress(courses, student)
    ranked = [(item, course.elective_block if isinstance(course.elective_block, str) else None)
              for item, course in candidates]
    candidate_count = sum(state in RECOMMENDABLE_STATUSES for state in statuses.values())
    if window is None:
        items = pick_items(ranked, k, required, taken, open_courses, chosen)
        _require_chosen(items, chosen, ranked)
        return {"what_if": bool(assumptions or skip or swap),
                "weights": weights,
                "candidate_count": candidate_count,
                "items": items,
                "not_eligible": _not_eligible(courses, details)}

    low, high = window
    items, left_out = pick_within_credits(ranked, high, required, taken, open_courses, chosen, skipped)
    _require_included(left_out, chosen, high)
    total = sum(term_credits(item) for item in items)
    credit_window = {"min_credits": low, "max_credits": high, "total_credits": total}
    names = dict(zip(courses["course_code"], courses["course_name"], strict=True))
    return {"what_if": bool(assumptions or skip or include),
            "weights": weights,
            "target_semester": semester_no,
            "credit_window": {**credit_window, "text": credit_window_text(credit_window)},
            "candidate_count": candidate_count,
            "items": items,
            "not_selected": _not_selected(left_out, blocks["block_name"].to_dict()),
            "not_eligible": _not_eligible(courses, details),
            "warnings": _warnings(student, window, total, names)}
