"""Sáu tiêu chí xếp hạng và lời giải thích đi kèm (hợp đồng mục 4.4).

Công thức của từng tiêu chí được đặc tả ở `docs/architecture/ranking.md`; đổi công thức thì tăng
`ALGORITHM_VERSION` ở `src/recommender/__init__.py`.

Mỗi hàm tiêu chí trả về một dict đúng bốn khóa `code`, `contribution`, `text`, `data`, hoặc `None`
khi tiêu chí không áp dụng. Hợp đồng cấm trả về lý do với `contribution = 0`, nên trọng số 0 cũng
làm tiêu chí vắng mặt khỏi `reasons`.

Tầng này KHÔNG đọc cơ sở dữ liệu: mọi hàm chỉ nhận giá trị Python thuần, nên `test/test_scoring.py`
chạy được mà không cần PostgreSQL.
"""
import math

from src.explain import format_decimal

# Bảng trọng số mặc định, lấy nguyên từ hợp đồng mục 6.6.
DEFAULT_WEIGHTS = {
    "outstanding_retake": 3.0,
    "overdue": 2.0,
    "on_time": 2.0,
    "unlocks": 1.5,
    "strong_topic": 1.0,
    "interest": 0.5,
}

# Mốc đạt trần của hai tiêu chí tính theo số lượng: mở khóa 10 học phần, hoặc trễ 2 học kỳ.
UNLOCKS_SATURATION = 10
OVERDUE_SATURATION = 2


def _reason(code, contribution, text, data):
    """Gói một lý do thành dict bốn khóa, làm tròn contribution 4 chữ số (mục 3.2).

    Trả `None` khi tiêu chí không góp điểm: mục 4.4 cấm trả về lý do với `contribution = 0`."""
    contribution = round(float(contribution), 4)
    if contribution <= 0:
        return None
    return {"code": code, "contribution": contribution, "text": text, "data": data}


def merge_weights(weights=None):
    """Ghép bảng trọng số client gửi với bảng mặc định (mục 6.6).

    Khóa thiếu lấy giá trị mặc định. Khóa lạ, giá trị âm hoặc không phải số là lỗi; tầng API
    chuyển `ValueError` thành `validation_error`."""
    merged = dict(DEFAULT_WEIGHTS)
    if not weights:
        return merged
    unknown = sorted(set(weights) - set(DEFAULT_WEIGHTS))
    if unknown:
        raise ValueError(f"Trọng số không có trong hợp đồng: {', '.join(unknown)}")
    for code, value in weights.items():
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Trọng số {code} phải là số, nhận được {value!r}") from error
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"Trọng số {code} phải lớn hơn hoặc bằng 0, nhận được {value!r}")
        merged[code] = number
    return merged


def outstanding_retake(last_attempt, weights):
    """Lý do `outstanding_retake`: học phần sinh viên đang nợ (mục 4.4).

    `last_attempt` là dict `term_code`, `score`, `attempt_no` của lần học gần nhất, hoặc `None`
    khi học phần không đang nợ. Môn đang nợ luôn góp đủ trọng số: nợ một kỳ hay ba kỳ đều cần
    xử lý ngay, và số lần đã học nằm trong `data` để người đọc tự thấy mức độ."""
    if not last_attempt:
        return None
    term_code = str(last_attempt["term_code"])
    score = last_attempt.get("score")
    data = {"term_code": term_code}
    if score is not None:
        data["score"] = float(score)
    data["attempt_no"] = int(last_attempt["attempt_no"])
    detail = f" (điểm {format_decimal(score)})" if score is not None else ""
    return _reason("outstanding_retake", weights["outstanding_retake"],
                   f"Bạn chưa đạt môn này ở học kỳ {term_code}{detail}.", data)


def schedule(recommended_semester, target_semester_no, weights):
    """Lý do `on_time` hoặc `overdue` (mục 4.4). Hai lý do loại trừ nhau nên hàm trả nhiều nhất một.

    Học phần mà khung dự kiến ở kỳ muộn hơn kỳ hiện tại của sinh viên không nhận lý do nào: chưa
    đến lúc học, nhưng cũng chưa trễ."""
    if recommended_semester is None or target_semester_no is None:
        return None
    recommended, target = int(recommended_semester), int(target_semester_no)
    data = {"recommended_semester": recommended, "target_semester": target}
    semesters_late = target - recommended
    if semesters_late == 0:
        return _reason("on_time", weights["on_time"],
                       f"Đúng kỳ dự kiến của chương trình (kỳ {target}).", data)
    if semesters_late < 0:
        return None
    level = min(1.0, semesters_late / OVERDUE_SATURATION)
    return _reason("overdue", weights["overdue"] * level,
                   f"Môn này dự kiến học ở kỳ {recommended}, bạn đang ở kỳ {target}.",
                   {**data, "semesters_late": semesters_late})


def unlocks(course_code, prerequisite_groups, weights):
    """Lý do `unlocks`: đạt học phần này mở khóa những học phần nào (mục 4.4).

    `prerequisite_groups` là dict mã học phần → `list[list[str]]` của cả khung. Đếm trên khung,
    không trừ môn sinh viên đã đạt: con số trả lời "môn này nằm ở đâu trong khung", là tính chất
    của chương trình chứ không của một sinh viên."""
    unlocked = sorted(code for code, groups in prerequisite_groups.items()
                      if any(course_code in group for group in groups))
    if not unlocked:
        return None
    level = min(1.0, len(unlocked) / UNLOCKS_SATURATION)
    return _reason("unlocks", weights["unlocks"] * level,
                   f"Đạt môn này sẽ mở khóa {len(unlocked)} học phần khác của chương trình.",
                   {"count": len(unlocked), "course_codes": unlocked})


def topic_strength(average_score, pass_score, max_score):
    """Mức vượt điểm đạt, chuẩn hóa về [0, 1]: đúng điểm đạt là 0, điểm tối đa là 1."""
    span = float(max_score) - float(pass_score)
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (float(average_score) - float(pass_score)) / span))


def strong_topic(topic, pass_score, max_score, weights):
    """Lý do `strong_topic`: học phần thuộc chủ đề sinh viên đang học tốt (mục 4.4).

    `topic` là dict `topic_code`, `topic_name`, `average_score`, `course_codes`, hoặc `None` khi
    học phần không có chủ đề chính, hoặc sinh viên chưa có điểm nào thuộc chủ đề đó."""
    if not topic:
        return None
    level = topic_strength(topic["average_score"], pass_score, max_score)
    studied = len(topic["course_codes"])
    return _reason("strong_topic", weights["strong_topic"] * level,
                   f"Bạn đang học tốt chủ đề {topic['topic_name']}: điểm trung bình "
                   f"{format_decimal(topic['average_score'])} trên {studied} môn đã học.",
                   {"topic_code": str(topic["topic_code"]), "topic_name": str(topic["topic_name"]),
                    "average_score": round(float(topic["average_score"]), 2),
                    "course_codes": sorted(topic["course_codes"])})


def interest(topic, weights):
    """Lý do `interest`: học phần thuộc chủ đề sinh viên tự khai (mục 4.4).

    Đây là tín hiệu PHỤ. Trọng số mặc định 0,5 so với 1,0 của `strong_topic` thể hiện thứ tự đó,
    và KHÔNG ĐƯỢC đảo: hệ thống gợi ý theo kết quả học tập, không theo lời khai."""
    if not topic:
        return None
    declared = float(topic["weight"])
    return _reason("interest", weights["interest"] * declared,
                   f"Thuộc chủ đề {topic['topic_name']} mà bạn đã khai là quan tâm.",
                   {"topic_code": str(topic["topic_code"]), "topic_name": str(topic["topic_name"]),
                    "weight": round(declared, 2)})


def sort_reasons(reasons):
    """Bỏ tiêu chí không áp dụng rồi sắp theo mục 3.3: `contribution` giảm dần, rồi `code` tăng dần."""
    return sorted((reason for reason in reasons if reason),
                  key=lambda reason: (-reason["contribution"], reason["code"]))


def total_score(reasons):
    """Điểm xếp hạng của một học phần: tổng `contribution`, làm tròn 4 chữ số (mục 6.6, quy định 2)."""
    return round(sum(reason["contribution"] for reason in reasons), 4)


def target_semester(year_of_study, term_no):
    """Vị trí của sinh viên trong lộ trình của khung, để so với `recommended_semester` (mục 3.1).

    Kỳ hè (`term_no` = 3) rơi vào cùng ô với kỳ 1 của năm sau; v1 chưa gợi ý cho kỳ hè nên chưa
    tách riêng."""
    return 2 * (int(year_of_study) - 1) + int(term_no)
