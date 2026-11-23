"""Câu tiếng Việt cho trạng thái học phần, vi phạm kế hoạch, môn không được xếp và cảnh báo (hợp đồng mục
6.5, 6.6, 6.7, 6.10, 6.11).

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
from decimal import ROUND_HALF_UP, Decimal

STATUSES = ("passed", "block_complete", "missing_prerequisite", "retake", "eligible")
VIOLATIONS = ("credit_limit_exceeded", "credit_below_minimum", "missing_prerequisite", "already_passed",
              "block_limit_exceeded", "duplicate_course", "not_in_curriculum")
NOT_SELECTED_REASONS = ("skipped", "block_full", "credit_budget")
WARNINGS = ("below_min_credits", "prerequisite_not_in_transcript", "studied_before_prerequisite")


def format_decimal(value: float, digits: int = 1) -> str:
    """Số thập phân viết kiểu Việt Nam, làm tròn nửa lên như khi đọc điểm: 3.0 thành "3,0", 5.25 thành "5,3".

    Không dùng `f"{value:.1f}"`: Python làm tròn nửa về số chẵn trên giá trị nhị phân, nên 5,25 thành "5,2"
    còn 2,45 lại thành "2,5" — cùng là một nửa mà người đọc không đoán được chiều làm tròn."""
    exact = Decimal(str(float(value)))
    return str(exact.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)).replace(".", ",")


def _missing(value) -> bool:
    """Điểm vắng mặt: `None`, hoặc NaN khi dữ liệu đi qua pandas."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def attempt_when(attempt: Mapping) -> str:
    """Lần học diễn ra lúc nào: "kỳ 2" với bảng điểm sinh viên tự nhập (mục 6.10, lần học có `semester`),
    "học kỳ 20252" với kết quả học tập trong cơ sở dữ liệu (mục 6.5, lần học có `term_code`)."""
    semester = attempt.get("semester")
    if semester is not None:
        return f"kỳ {int(semester)}"
    return f"học kỳ {attempt['term_code']}"


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
        return f"Cần học lại {name}: bạn chưa đạt môn này ở {attempt_when(attempt)}{score}."
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
    `None` khi vi phạm không gắn với một môn cụ thể hay mã không thuộc khung. Trường cần có trong `data`, đúng
    tên trường mà `check_plan()` của tầng luật trả về:

    | `code` | `data` |
    | --- | --- |
    | `credit_limit_exceeded` | `total_credits`, `max_credits_per_term`; mục 6.12 thay bằng `max_credits` |
    | `credit_below_minimum` | `total_credits`, `min_credits` |
    | `missing_prerequisite` | `missing_prerequisites` |
    | `block_limit_exceeded` | `block_code`, `required_credits`, `total_credits`; `block_name` nếu có |
    | `duplicate_course` | `occurrence`: lần xuất hiện thứ mấy, mỗi lần lặp là một vi phạm |

    Ở mục 6.12 sinh viên tự đặt khoảng tín chỉ, nên `credit_limit_exceeded` so với `max_credits` của khoảng đó
    và câu nói "bạn đặt"; `credit_below_minimum` không gắn với môn nào (`course_code` là `None`).

    `total_credits` của `block_limit_exceeded` là tín chỉ của khối sau khi thêm môn này: đã đạt cộng môn của
    khối đứng trước trong kế hoạch cộng chính nó. Tầng luật chưa gửi `block_name` thì câu gọi khối bằng mã.
    """
    code, data = violation["code"], violation.get("data", {})
    name = course["course_name"] if course else violation.get("course_code")
    if code == "credit_limit_exceeded":
        if "max_credits" in data:
            limit, whose = data["max_credits"], "tín chỉ bạn đặt cho học kỳ này"
        else:
            limit, whose = data["max_credits_per_term"], "tín chỉ một học kỳ"
        return (f"Kế hoạch có {data['total_credits']} tín chỉ, vượt mức tối đa {limit} {whose}: "
                f"cần bỏ bớt ít nhất {data['total_credits'] - limit} tín chỉ.")
    if code == "credit_below_minimum":
        return (f"Kế hoạch có {data['total_credits']} tín chỉ, chưa đủ mức tối thiểu {data['min_credits']} tín chỉ "
                f"bạn đặt: cần thêm ít nhất {data['min_credits'] - data['total_credits']} tín chỉ.")
    if code == "missing_prerequisite":
        phrase = prerequisite_phrase(data["missing_prerequisites"], names)
        return f"{name} chưa học được: cần hoàn thành {phrase} trước."
    if code == "already_passed":
        return f"Bạn đã đạt {name}: bỏ khỏi kế hoạch."
    if code == "block_limit_exceeded":
        block = _block_phrase(data.get("block_name") or data["block_code"])
        return (f"{block[0].upper() + block[1:]} chỉ cần {data['required_credits']} tín chỉ, thêm {name} đưa tổng "
                f"của khối lên {data['total_credits']}: bỏ bớt môn của khối này.")
    if code == "duplicate_course":
        return f"{name} xuất hiện lần thứ {data['occurrence']} trong kế hoạch: bỏ lần lặp này."
    if code == "not_in_curriculum":
        return f"Học phần {violation['course_code']} không thuộc chương trình đào tạo của bạn: bỏ khỏi kế hoạch."
    raise ValueError(f"Mã vi phạm không có trong hợp đồng (mục 4.5): {code!r}")


def not_selected_text(course: Mapping, reason: str, data: Mapping) -> str:
    """Câu `text` cho một học phần học được nhưng không được xếp vào học kỳ đang gợi ý (mục 6.11, `not_selected`).

    `course` cần `course_name`. `reason` là một mã của mục 4.6, `data` là dữ liệu đi kèm mã đó:

    | `reason` | `data` |
    | --- | --- |
    | `skipped` | rỗng |
    | `block_full` | `block_code`, `block_name`, `required_credits`, `taken_credits`, `credits` |
    | `credit_budget` | `credits`, `total_credits`, `max_credits` |

    `taken_credits` và `total_credits` là số SAU khi đã xếp xong: thêm môn này vào kết quả cuối cùng vẫn
    vi phạm, nên câu nói đúng về chính danh sách sinh viên đang xem."""
    name = course["course_name"]
    if reason == "skipped":
        return f"Bạn chọn chưa học {name} ở kỳ này."
    if reason == "block_full":
        block = _block_phrase(data.get("block_name") or data["block_code"])
        required, taken = data["required_credits"], data["taken_credits"]
        if taken + data["credits"] > required:
            return (f"Chưa xếp {name}: {block} chỉ cần {required} tín chỉ và đã có {taken} từ môn đã đạt "
                    f"và môn xếp trên.")
        return (f"Chưa xếp {name}: {block} cần đúng {required} tín chỉ, đã có {taken}; thêm môn này "
                f"({data['credits']} tín chỉ) thì phần còn thiếu không ghép đúng được bằng các môn còn lại.")
    if reason == "credit_budget":
        return (f"Chưa xếp {name}: kỳ này đã có {data['total_credits']} tín chỉ, thêm {data['credits']} tín chỉ "
                f"sẽ vượt mức tối đa {data['max_credits']} bạn đặt.")
    raise ValueError(f"Lý do không xếp không có trong hợp đồng (mục 4.6): {reason!r}")


def warning_text(warning: Mapping, names: Mapping[str, str]) -> str:
    """Câu `text` cho một cảnh báo (mục 4.7). Cảnh báo không chặn kết quả, chỉ báo điều sinh viên nên kiểm lại.

    | `code` | `data` |
    | --- | --- |
    | `below_min_credits` | `min_credits`, `total_credits` |
    | `prerequisite_not_in_transcript` | `missing_prerequisites` |
    | `studied_before_prerequisite` | `semester`, `prerequisite_code`, `prerequisite_semester` |
    """
    code, data = warning["code"], warning.get("data", {})
    name = names.get(warning.get("course_code"), warning.get("course_code"))
    if code == "below_min_credits":
        return (f"Chỉ xếp được {data['total_credits']} tín chỉ, thấp hơn mức tối thiểu {data['min_credits']} bạn "
                f"đặt: không còn môn học được nào vừa với mức tối đa và luật khối tự chọn.")
    if code == "prerequisite_not_in_transcript":
        phrase = prerequisite_phrase(data["missing_prerequisites"], names)
        return f"Bảng điểm ghi đã đạt {name} nhưng chưa đạt {phrase}: kiểm tra lại bảng điểm."
    if code == "studied_before_prerequisite":
        return (f"{name} ghi học ở kỳ {data['semester']}, không sau kỳ {data['prerequisite_semester']} của môn "
                f"tiên quyết {_course_label(data['prerequisite_code'], names)}: kiểm tra lại kỳ học.")
    raise ValueError(f"Mã cảnh báo không có trong hợp đồng (mục 4.7): {code!r}")


def credit_window_text(window: Mapping) -> str:
    """Câu `text` của `credit_window` (mục 6.11): tổng tín chỉ đã xếp so với khoảng sinh viên đặt."""
    total, low, high = window["total_credits"], window["min_credits"], window["max_credits"]
    if total < low:
        return f"Tổng {total} tín chỉ, thấp hơn mức tối thiểu {low} bạn đặt."
    return f"Tổng {total} tín chỉ, trong khoảng {low}–{high} bạn đặt."
