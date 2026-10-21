"""Chọn nhiều nhất `k` học phần từ danh sách đã xếp hạng, giữ đúng luật khối tự chọn.

Khối `choose_credits` phải chọn ĐÚNG `required_credits` tín chỉ (hợp đồng mục 6.2), nên đây là ràng buộc
cứng: không trọng số nào đưa được một môn làm hỏng khối vào danh sách gợi ý (mục 6.6, quy định 1).

Tầng này KHÔNG đọc cơ sở dữ liệu, nên `test/test_selection.py` chạy được mà không cần PostgreSQL.
"""
from src.rules.status import fits_in_block


def reachable_sums(credits: list[int]) -> set[int]:
    """Mọi tổng tín chỉ ghép được từ một nhóm học phần, mỗi môn dùng nhiều nhất một lần, kể cả tổng 0."""
    sums = {0}
    for value in credits:
        sums |= {total + value for total in sums}
    return sums


def fits_elective_block(credits: int, taken: int, required: int, others: list[int]) -> bool:
    """Nhận thêm một môn `credits` tín chỉ vào khối tự chọn đang có `taken` tín chỉ được không.

    Nhận khi môn đó không làm khối vượt `required`, VÀ phần còn thiếu sau đó vẫn ghép được đúng bằng
    `others` — tín chỉ của các môn khác trong khối chưa đạt và chưa được chọn. Điều kiện thứ hai là chỗ dễ
    bỏ sót: khối cần 5 tín chỉ gồm môn 2 và 3 tín chỉ, đã có 2 thì nhận môn 3 (đủ 5), nhưng không nhận thêm
    môn 2 (lên 4, còn thiếu 1 mà không môn nào đủ nhỏ, nên khối không bao giờ hoàn thành đúng được nữa).

    Điều kiện thứ nhất là `rules.fits_in_block()`, để tầng xếp hạng và tầng luật không thể hiểu "vượt khối"
    theo hai cách. Điều kiện thứ hai chỉ có ở đây: một kế hoạch làm khối kẹt lại chưa vi phạm luật nào, nhưng
    gợi ý nó thì sinh viên không đi tiếp được.
    """
    return fits_in_block(credits, taken, required) and required - (taken + credits) in reachable_sums(others)


def pick_items(ranked: list[tuple[dict, str | None]], k: int, required: dict[str, int],
               taken: dict[str, int], open_courses: dict[str, dict[str, int]]) -> list[dict]:
    """Đi từ trên xuống `ranked`, lấy nhiều nhất `k` phần tử, bỏ qua môn làm hỏng khối tự chọn.

    `ranked` là list `(item, mã khối tự chọn hoặc None)` đã sắp theo mục 3.3; `item` có `course_code` và
    `credits`. `required`: mã khối → số tín chỉ phải chọn. `taken`: mã khối → tín chỉ đã đạt.
    `open_courses`: mã khối → {mã môn: tín chỉ} của mọi môn trong khối chưa đạt, kể cả môn chưa đủ điều kiện
    tiên quyết — khối có thể hoàn thành bằng chúng ở các kỳ sau.

    Chọn tham lam chứ không tìm tổ hợp tối ưu, để lời giải thích luôn nói được: "môn này không được gợi ý
    vì các môn xếp trên nó đã chiếm chỗ trong khối". Không sửa tham số nào; trả về bản sao đã điền `rank`.
    """
    taken = dict(taken)
    open_courses = {block: dict(courses) for block, courses in open_courses.items()}
    picked = []
    for item, block in ranked:
        if len(picked) >= k:
            break
        if block in required:
            pending = open_courses.get(block, {})
            others = [value for code, value in pending.items() if code != item["course_code"]]
            if not fits_elective_block(item["credits"], taken.get(block, 0), int(required[block]), others):
                continue
            taken[block] = taken.get(block, 0) + item["credits"]
            pending.pop(item["course_code"], None)
        picked.append({**item, "rank": len(picked) + 1})
    return picked
