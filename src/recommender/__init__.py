"""Tầng xếp hạng: chọn học phần nên học ở học kỳ tới và giải thích vì sao.

Hàm công bố cho tầng API (mục 6.6) và cho `test/test_recommender_contract.py`:

    recommend(repo, student, k=5, weights=None, status=None, term_code=None) -> list[dict]

`student` là một dòng của `repo.students()`. Trạng thái học phần do `src/rules/status.py` quyết định;
tầng này chỉ xếp hạng trong số học phần đã được phép gợi ý. Công thức của sáu tiêu chí:
`docs/architecture/ranking.md`.
"""
import pandas as pd

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
from src.recommender.selection import pick_items
from src.rules.status import course_status, elective_credits_passed

# Tầng API đọc hai hằng số này cho GET /v1/meta (mục 6.1).
ALGORITHM = "rule_based_weighted"
ALGORITHM_VERSION = "1.0.1"

# Chỉ hai trạng thái này được vào danh sách gợi ý (mục 6.6, quy định 1).
RECOMMENDABLE_STATUSES = ("retake", "eligible")

# Học phần khung không ghi kỳ dự kiến thì xếp sau cùng khi hai học phần bằng điểm (mục 3.3).
MISSING_SEMESTER = 10**6

__all__ = ["ALGORITHM", "ALGORITHM_VERSION", "DEFAULT_WEIGHTS", "recommend"]


def _recommended_semester(course):
    """Kỳ dự kiến của một học phần trong khung, `None` khi khung không ghi."""
    value = getattr(course, "recommended_semester", None)
    return None if value is None or pd.isna(value) else int(value)


def _semester_key(course):
    """Khóa sắp xếp theo kỳ dự kiến; học phần không ghi kỳ xếp sau cùng (mục 3.3)."""
    semester = _recommended_semester(course)
    return MISSING_SEMESTER if semester is None else semester


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
    """Chủ đề sinh viên tự khai: mã chủ đề → dict sẵn sàng cho `scoring.interest`."""
    declared = repo.student_interests(student["student_id"])
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


def recommend(repo, student, k=5, weights=None, status=None, term_code=None):
    """Học phần nên học ở học kỳ tới, mỗi phần tử kèm điểm và lời giải thích (mục 6.6).

    `k` là số phần tử tối đa. `weights` gửi một phần được: khóa thiếu lấy mặc định, khóa lạ hoặc
    giá trị âm làm hàm raise `ValueError`. `status` nhận sẵn kết quả của `course_status` để không
    phải tính lại; để `None` thì hàm tự tính.

    `student` phải được đọc ở cùng học kỳ với `term_code`, tức `repo.student(uni, code, term_code)`:
    `year_of_study`, các môn đã đạt và lần học gần nhất đều tính theo mốc đó (mục 3.1). `term_code` để
    `None` là học kỳ cần gợi ý.

    Trả về list[dict] đã sắp theo mục 3.3, mỗi dict có `rank`, `course_code`, `course_name`,
    `credits`, `block_code`, `status`, `score`, `reasons`.
    """
    weights = merge_weights(weights)
    curriculum_code = student["curriculum_code"]
    courses = repo.curriculum_courses(curriculum_code)
    statuses = course_status(repo, student) if status is None else status
    grading = repo.curriculum(curriculum_code)
    term = repo.term(student["university_code"], term_code or repo.setting("target_term_code"))
    semester_no = target_semester(student["year_of_study"], term["term_no"])
    prerequisites = dict(zip(courses["course_code"], courses["prerequisite_groups"], strict=True))
    attempts = student["latest_attempts"]
    strong = _strong_topics(repo, courses, attempts)
    declared = _declared_topics(repo, student)

    candidates = []
    for course in courses.itertuples():
        state = statuses.get(course.course_code)
        if state not in RECOMMENDABLE_STATUSES:
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

    required = repo.elective_blocks(curriculum_code).set_index("block_code")["required_credits"].to_dict()
    taken, open_courses = _elective_progress(courses, student)
    ranked = [(item, course.elective_block if isinstance(course.elective_block, str) else None)
              for item, course in candidates]
    return pick_items(ranked, k, required, taken, open_courses)
