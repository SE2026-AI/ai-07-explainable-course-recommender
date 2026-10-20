"""Câu tiếng Việt cho trạng thái học phần và vi phạm kế hoạch (hợp đồng mục 6.5, 6.6, 6.7).

Tầng này chỉ dựng câu chữ từ dữ liệu mà tầng luật và tầng xếp hạng đã tính; nó KHÔNG quyết định môn nào
được học hay được gợi ý. Mọi hàm là hàm thuần, không đọc database, nên `test/test_explain.py` chạy được
mà không cần PostgreSQL.

README đặt bốn tiêu chí cho một lời giải thích: trung thực, cụ thể, hành động được, nhất quán. Vì vậy mỗi
câu nêu tên môn và con số thật, câu "chưa học được" và câu vi phạm luôn nói cần làm gì, và cùng một tình
huống luôn đi qua cùng một hàm. Đổi câu chữ ở đây là đổi cách dựng lời giải thích: tăng
`ALGORITHM_VERSION` (`docs/architecture/ranking.md` mục 7).
"""
import math
from collections.abc import Mapping, Sequence

STATUSES = ("passed", "block_complete", "missing_prerequisite", "retake", "eligible")
VIOLATIONS = ("credit_limit_exceeded", "missing_prerequisite", "already_passed",
              "block_limit_exceeded", "duplicate_course", "not_in_curriculum")


def format_decimal(value: float, digits: int = 1) -> str:
    """Số thập phân viết kiểu Việt Nam: 3.0 thành "3,0"."""
    return f"{float(value):.{digits}f}".replace(".", ",")


def _missing(value) -> bool:
    """Điểm vắng mặt: `None`, hoặc NaN khi dữ liệu đi qua pandas."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def _course_label(code: str, names: Mapping[str, str]) -> str:
    """"Xác suất - Thống kê (MAT2323)"; chỉ còn mã khi không tra được tên."""
    name = names.get(code)
    return f"{name} ({code})" if name else code


def _join_and(parts: Sequence[str]) -> str:
    """"A", "A và B", "A, B và C"."""
    if len(parts) <= 1:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} và {parts[-1]}"


def _block_phrase(block_name: str) -> str:
    """"khối Ngoại ngữ B1"; tên đã mở đầu bằng "Khối" thì không lặp lại chữ đó."""
    if block_name.lower().startswith("khối "):
        return block_name[0].lower() + block_name[1:]
    return f"khối {block_name}"


def prerequisite_phrase(groups: Sequence[Sequence[str]], names: Mapping[str, str]) -> str:
    """Các nhóm tiên quyết thành một cụm từ, giữ đúng VÀ/HOẶC của hợp đồng mục 4.2.

    Các nhóm nối bằng "và". Nhóm nhiều mã nói rõ "một trong hai môn … hoặc …", để "A và B hoặc C" không
    bị đọc nhầm thành "(A và B) hoặc C". Thứ tự giữ nguyên như dữ liệu gửi vào."""
    if not groups or any(not group for group in groups):
        raise ValueError(f"Nhóm tiên quyết rỗng, không diễn đạt được: {groups!r}")
    parts = []
    for group in groups:
        labels = [_course_label(code, names) for code in group]
        if len(labels) == 1:
            parts.append(labels[0])
        else:
            lead = "một trong hai môn" if len(labels) == 2 else "một trong các môn"
            parts.append(f"{lead} {', '.join(labels[:-1])} hoặc {labels[-1]}")
    return _join_and(parts)


def status_text(course: Mapping, detail: Mapping, names: Mapping[str, str]) -> str:
    """Câu `text` cho một dòng của `course-status` (mục 6.5) và của `not_eligible` (mục 6.6).

    `course` cần `course_name`; có `prerequisite_groups` thì câu `eligible` phân biệt được môn có và không
    có điều kiện tiên quyết. `detail` là một giá trị của `rules.course_status_details()`: `status`, kèm
    `missing_prerequisites`, `block` hoặc `last_attempt` tùy trạng thái. `names` tra mã → tên học phần,
    dùng cho các môn tiên quyết."""
    name, status = course["course_name"], detail["status"]
    if status == "passed":
        attempt = detail.get("last_attempt")
        if attempt is None:
            return f"Đã đạt {name}."
        if _missing(attempt.get("score")):
            return f"Đã đạt {name} (được miễn)."
        return f"Đã đạt {name} (điểm {format_decimal(attempt['score'])})."
    if status == "retake":
        attempt = detail["last_attempt"]
        score = "" if _missing(attempt.get("score")) else f" (điểm {format_decimal(attempt['score'])})"
        return f"Cần học lại {name}: bạn chưa đạt môn này ở học kỳ {attempt['term_code']}{score}."
    if status == "missing_prerequisite":
        phrase = prerequisite_phrase(detail["missing_prerequisites"], names)
        return f"Chưa học được {name}: cần hoàn thành {phrase} trước."
    if status == "block_complete":
        block = detail["block"]
        return (f"Không cần học {name}: {_block_phrase(block['block_name'])} đã đủ "
                f"{block['earned_credits']}/{block['required_credits']} tín chỉ.")
    if status == "eligible":
        if course.get("prerequisite_groups"):
            return f"Học được {name}: đã đủ điều kiện tiên quyết."
        return f"Học được {name}: môn này không có điều kiện tiên quyết."
    raise ValueError(f"Trạng thái học phần không có trong hợp đồng (mục 4.1): {status!r}")


def violation_text(violation: Mapping, course: Mapping | None, names: Mapping[str, str]) -> str:
    """Câu `text` cho một vi phạm của `plan-check` (mục 6.7; mã vi phạm ở mục 4.5).

    `violation` có `code`, `course_code` và `data`. `course` là dòng của học phần đó trong khung, hoặc
    `None` khi vi phạm không gắn với một môn cụ thể hay mã không thuộc khung. Trường cần có trong `data`:

    | `code` | `data` |
    | --- | --- |
    | `credit_limit_exceeded` | `total_credits`, `max_credits_per_term` |
    | `missing_prerequisite` | `missing_prerequisites` |
    | `block_limit_exceeded` | `block_name`, `required_credits`, `planned_credits` |
    | `duplicate_course` | `count` |
    """
    code, data = violation["code"], violation.get("data", {})
    name = course["course_name"] if course else violation.get("course_code")
    if code == "credit_limit_exceeded":
        over = data["total_credits"] - data["max_credits_per_term"]
        return (f"Kế hoạch có {data['total_credits']} tín chỉ, vượt mức tối đa {data['max_credits_per_term']} "
                f"tín chỉ một học kỳ: cần bỏ bớt ít nhất {over} tín chỉ.")
    if code == "missing_prerequisite":
        phrase = prerequisite_phrase(data["missing_prerequisites"], names)
        return f"{name} chưa học được: cần hoàn thành {phrase} trước."
    if code == "already_passed":
        return f"Bạn đã đạt {name}: bỏ khỏi kế hoạch."
    if code == "block_limit_exceeded":
        block = _block_phrase(data["block_name"])
        return (f"{block[0].upper() + block[1:]} chỉ cần {data['required_credits']} tín chỉ, kế hoạch đưa tổng lên "
                f"{data['planned_credits']}: bỏ bớt môn của khối này.")
    if code == "duplicate_course":
        return f"{name} xuất hiện {data['count']} lần trong kế hoạch: chỉ giữ một."
    if code == "not_in_curriculum":
        return f"Học phần {violation['course_code']} không thuộc chương trình đào tạo của bạn: bỏ khỏi kế hoạch."
    raise ValueError(f"Mã vi phạm không có trong hợp đồng (mục 4.5): {code!r}")
