"""Chọn học phần từ danh sách đã xếp hạng, giữ đúng luật khối tự chọn: nhiều nhất `k` môn (`pick_items`,
mục 6.6) hoặc trong khoảng tín chỉ sinh viên đặt (`pick_within_credits`, mục 6.11).

Khối `choose_credits` phải chọn ĐÚNG `required_credits` tín chỉ (hợp đồng mục 6.2), nên đây là ràng buộc
cứng: không trọng số nào đưa được một môn làm hỏng khối vào danh sách gợi ý (mục 6.6, quy định 1).

Tầng này KHÔNG đọc cơ sở dữ liệu, nên `test/test_selection.py` chạy được mà không cần PostgreSQL.
"""
from collections.abc import Collection

from src.rules.plan import term_credits
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
               taken: dict[str, int], open_courses: dict[str, dict[str, int]],
               chosen: Collection[str] = ()) -> list[dict]:
    """Đi từ trên xuống `ranked`, lấy nhiều nhất `k` phần tử, bỏ qua môn làm hỏng khối tự chọn.

    `ranked` là list `(item, mã khối tự chọn hoặc None)` đã sắp theo mục 3.3; `item` có `course_code` và
    `credits`. `required`: mã khối → số tín chỉ phải chọn. `taken`: mã khối → tín chỉ đã đạt.
    `open_courses`: mã khối → {mã môn: tín chỉ} của mọi môn trong khối chưa đạt, kể cả môn chưa đủ điều kiện
    tiên quyết — khối có thể hoàn thành bằng chúng ở các kỳ sau.

    `chosen` là mã các môn sinh viên chọn học thay (`swap`, mục 6.6). Chúng được xét trước mọi môn khác nên
    luôn có chỗ, và chiếm tín chỉ của khối tự chọn trước; luật khối vẫn áp như mọi môn, nên môn chọn thay làm
    hỏng khối thì vắng mặt và người gọi phải báo lỗi. Danh sách trả về vẫn theo thứ tự của `ranked`.

    Chọn tham lam chứ không tìm tổ hợp tối ưu, để lời giải thích luôn nói được: "môn này không được gợi ý
    vì các môn xếp trên nó đã chiếm chỗ trong khối". Không sửa tham số nào; trả về bản sao đã điền `rank`.
    """
    taken = dict(taken)
    open_courses = {block: dict(courses) for block, courses in open_courses.items()}
    accepted = set()
    first = [pair for pair in ranked if pair[0]["course_code"] in chosen]
    rest = [pair for pair in ranked if pair[0]["course_code"] not in chosen]
    for item, block in first + rest:
        if len(accepted) >= k:
            break
        if block in required:
            pending = open_courses.get(block, {})
            others = [value for code, value in pending.items() if code != item["course_code"]]
            if not fits_elective_block(item["credits"], taken.get(block, 0), int(required[block]), others):
                continue
            taken[block] = taken.get(block, 0) + item["credits"]
            pending.pop(item["course_code"], None)
        accepted.add(item["course_code"])
    picked = [item for item, _ in ranked if item["course_code"] in accepted]
    return [{**item, "rank": rank} for rank, item in enumerate(picked, start=1)]


def pick_within_credits(ranked: list[tuple[dict, str | None]], max_credits: int, required: dict[str, int],
                        taken: dict[str, int], open_courses: dict[str, dict[str, int]],
                        chosen: Collection[str] = (), skipped: Collection[str] = ()
                        ) -> tuple[list[dict], list[tuple[dict, str, dict]]]:
    """Đi từ trên xuống `ranked`, nhận môn khi tổng tín chỉ vẫn không vượt `max_credits` và khối tự chọn vẫn
    hoàn thành đúng được (mục 6.11). Trả về `(items, left_out)`.

    Khác `pick_items()` ở chỗ dừng theo tín chỉ chứ không theo số môn, và môn không vừa thì bỏ qua rồi XÉT
    TIẾP: còn trống 2 tín chỉ thì môn 2 tín chỉ xếp dưới vẫn vào được. Các tham số còn lại như `pick_items()`.
    `chosen` là các môn sinh viên muốn học (`include`), xét trước mọi môn khác. `skipped` là các môn sinh viên
    chưa muốn học kỳ này (`skip`): vẫn nằm trong `ranked` để giữ đúng thứ tự, nhưng không bao giờ được nhận.

    `left_out` liệt kê mọi phần tử không vào `items`, theo thứ tự của `ranked`, mỗi phần tử một bộ
    `(item, reason, data)` với `reason` là đúng một mã của mục 4.6, xét theo thứ tự `skipped`, `block_full`,
    `credit_budget`. `data` của hai mã sau tính trên kết quả CUỐI CÙNG: tín chỉ chỉ tăng dần trong lúc chọn,
    nên môn đã không vừa lúc được xét thì cũng không vừa với danh sách sau cùng. Môn `chosen` nằm trong
    `left_out` nghĩa là lựa chọn đó sai; người gọi phải báo lỗi. Không sửa tham số nào.
    """
    taken = dict(taken)
    open_courses = {block: dict(courses) for block, courses in open_courses.items()}
    accepted, refused, total = set(), {}, 0
    first = [pair for pair in ranked if pair[0]["course_code"] in chosen]
    rest = [pair for pair in ranked if pair[0]["course_code"] not in chosen]
    for item, block in first + rest:
        code, credits = item["course_code"], item["credits"]
        if code in skipped:
            refused[code] = "skipped"
            continue
        if block in required:
            pending = open_courses.get(block, {})
            others = [value for other, value in pending.items() if other != code]
            if not fits_elective_block(credits, taken.get(block, 0), int(required[block]), others):
                refused[code] = "block_full"
                continue
        # Tín chỉ chiếm trong tổng của học kỳ theo đúng luật của kiểm tra kế hoạch (mục 6.7, 6.12).
        cost = term_credits(item)
        if total + cost > max_credits:
            refused[code] = "credit_budget"
            continue
        if block in required:
            taken[block] = taken.get(block, 0) + credits
            open_courses.get(block, {}).pop(code, None)
        total += cost
        accepted.add(code)

    picked = [item for item, _ in ranked if item["course_code"] in accepted]
    items = [{**item, "rank": rank} for rank, item in enumerate(picked, start=1)]
    left_out = []
    for item, block in ranked:
        reason = refused.get(item["course_code"])
        if reason == "skipped":
            data = {}
        elif reason == "block_full":
            data = {"block_code": block, "required_credits": int(required[block]),
                    "taken_credits": taken.get(block, 0), "credits": item["credits"]}
        elif reason == "credit_budget":
            data = {"credits": item["credits"], "total_credits": total, "max_credits": max_credits}
        else:
            continue
        left_out.append((item, reason, data))
    return items, left_out
