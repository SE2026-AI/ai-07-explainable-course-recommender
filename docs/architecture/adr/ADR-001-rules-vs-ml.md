# ADR-001 — Rule-based scoring vs ML recommender

**Status:** Accepted 2026-10-06 (nhóm trưởng duyệt, T-00) · **Date:** 2026-10-06 · **Supersedes:** mở rộng D-03 trong `../DECISIONS.md` · **Related:** `../RECOMMENDER_DESIGN.md`, `../FAIRNESS.md`

## Context

AI-07 phải gợi ý môn học từ mục tiêu và lịch sử học **giả lập**, giải thích điều kiện tiên quyết và cho người dùng chỉnh ưu tiên (what-if). Đề bài yêu cầu một ADR so sánh rules và ML.

Ràng buộc thực tế:
- **Không có dữ liệu thật.** Không có lịch sử đăng ký, điểm hay phản hồi của sinh viên thật; mọi dữ liệu là synthetic. Một mô hình ML học trên dữ liệu synthetic chỉ học lại chính quy tắc đã dùng để sinh dữ liệu.
- **Giải thích là yêu cầu cốt lõi.** Mỗi đề xuất phải chỉ ra được thành phần điểm, bằng chứng trong catalog và tiên quyết còn thiếu.
- **What-if phải tất định.** Đổi trọng số thì kết quả phải thay đổi theo cách người dùng dự đoán được, baseline không đổi.
- **Tiên quyết là ràng buộc cứng.** Không mô hình nào được phép xếp hạng môn chưa đủ điều kiện lên danh sách "học được ngay".
- Nhóm 4 người, độ khó trung bình, cần kiểm thử được bằng oracle tính tay.

## Options

| Tiêu chí | A. Rules + weighted scoring | B. Content-based (TF-IDF/embedding tương đồng) | C. Collaborative filtering (MF/kNN) | D. Learning-to-rank (GBDT/LambdaMART) | E. Hybrid: rules gate + ML score |
|---|---|---|---|---|---|
| Cần dữ liệu tương tác thật | Không | Không (chỉ cần mô tả môn) | **Có**, nhiều | **Có**, có nhãn | Có (phần ML) |
| Cold-start (sinh viên mới, môn mới) | Tốt | Tốt | Kém | Kém | Trung bình |
| Giải thích được theo thành phần | **Đầy đủ**, cộng tuyến tính | Một phần (độ tương đồng) | Kém ("người giống bạn đã học") | Cần SHAP, xấp xỉ | Phần gate rõ, phần điểm mờ |
| What-if tất định, dễ hiểu | **Có** | Có, nhưng khó dự đoán | Không tự nhiên | Không tự nhiên | Một phần |
| Kiểm thử bằng oracle tính tay | **Có** | Một phần | Không | Không | Phần gate |
| Fairness kiểm soát được | Cao: chỉ dùng đặc trưng được khai báo | Trung bình | Thấp: khuếch đại thiên lệch lịch sử | Thấp–trung bình | Trung bình |
| Chi phí xây dựng/vận hành | Thấp | Thấp–trung bình | Trung bình | Cao | Cao |

## Decision

Chọn **A: rules + weighted scoring tất định**, với tiên quyết là cổng cứng chạy trước xếp hạng.
- 4 thành phần `goal_match`, `interest_match`, `preparation`, `workload_fit` đều chuẩn hóa về `[0,1]` và cộng có trọng số. Chi tiết công thức trong `RECOMMENDER_DESIGN.md`.
- `interest_match` dùng Jaccard trên tag, tức là đã có yếu tố **content-based đơn giản** (B ở mức tối thiểu) mà vẫn giải thích được.
- Không dùng C, D trong v0.1, vì không có dữ liệu tương tác thật; huấn luyện trên dữ liệu synthetic không tạo được bằng chứng.

## Consequences

- (+) Mọi điểm đều tái lập được: cùng `catalog_version`, `algorithm_version` và input thì cho cùng output; có thể đối chiếu với bảng tính tay (ví dụ ST201 = .86, SE201 = .58).
- (+) Giải thích sinh từ chính các thành phần điểm, không có lý do "bịa".
- (+) Fairness kiểm tra được bằng cách chứng minh hàm điểm không đọc thuộc tính nhóm (xem `FAIRNESS.md`).
- (−) Trọng số mặc định (.50/.20/.10/.20) và bảng ánh xạ mục tiêu → môn là do người đặt, không học từ dữ liệu, nên có thể chưa tối ưu.
- (−) Không cá nhân hóa theo hành vi của sinh viên tương tự.

## Evidence plan (để ADR có số liệu, không chỉ lập luận)

Ticket `T-14` trong `docs/tasks/BACKLOG.md`: chạy một baseline ML nhỏ (ví dụ logistic regression hoặc kNN) trên dữ liệu synthetic do `tools/generate_synthetic_data.py` sinh ra, rồi so với rules theo 3 chỉ số:
1. Tỷ lệ đề xuất vi phạm tiên quyết trước khi lọc (rules luôn bằng 0).
2. Tỷ lệ đề xuất có giải thích đối chiếu được với bằng chứng.
3. Độ ổn định thứ hạng khi đổi một trọng số.

Kết quả ghi vào mục "Results" bên dưới. Nếu baseline ML không vượt rules ở chỉ số nào có ý nghĩa thì giữ quyết định A.

## Revisit when

- Có dữ liệu đăng ký hoặc phản hồi thật đã được phép sử dụng và đủ lớn → cân nhắc E (rules gate + LTR), nhưng giữ cổng tiên quyết và giải thích theo thành phần.
- Người dùng cần nhập mục tiêu dạng văn bản tự do → cân nhắc mô hình ngôn ngữ chỉ để **ánh xạ văn bản sang goal ID**, có fallback, không được thay đổi điểm hay tiên quyết.

## Results

_Chưa chạy. Điền sau khi hoàn thành T-14._
