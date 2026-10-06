# Fairness Checks — Proposed 0.1

**Status:** Accepted 2026-10-06 (T-00); kiểm tra chưa chạy. Mọi ngưỡng dưới đây là đề xuất, không phải kết quả đo. **Related:** `adr/ADR-001-rules-vs-ml.md`, `RECOMMENDER_DESIGN.md`, `RELIABILITY.md`.

## Mục tiêu

Gợi ý môn chỉ được phụ thuộc vào **dữ liệu học thuật và lựa chọn của chính sinh viên** (lịch sử, mục tiêu, sở thích, ưu tiên khối lượng, trần tín chỉ). Hai sinh viên có cùng các yếu tố đó phải nhận cùng kết quả, bất kể thuộc nhóm nào. Hệ thống cũng không được để một nhóm hồ sơ liên tục chỉ nhận được một tập môn hẹp nếu không có lý do học thuật.

## Thuộc tính nhóm (chỉ dùng cho kiểm thử)

Dữ liệu synthetic gắn nhãn nhóm trong file **sidecar** `cohorts.json`, tách khỏi profile. Schema `Profile` trong OpenAPI có `additionalProperties: false`, nên API không thể nhận các nhãn này.

| Nhãn | Giá trị | Vì sao kiểm |
|---|---|---|
| `gender` | `F`, `M`, `X` | Thuộc tính nhạy cảm; không được ảnh hưởng điểm |
| `region` | `urban`, `rural` | Thuộc tính nhạy cảm/gián tiếp |
| `academic_pattern` | `strong`, `average`, `has_failed` | Không nhạy cảm, nhưng cần đảm bảo nhóm có môn rớt vẫn nhận gợi ý hữu ích, không bị "bỏ rơi" |

Nhãn `gender`/`region` được sinh **độc lập** với lịch sử học trong v0.1. Nếu sau này mô phỏng tương quan (ví dụ vùng ảnh hưởng điểm), phải ghi rõ trong báo cáo.

## Các kiểm tra

| ID | Kiểm tra | Cách làm | Ngưỡng đề xuất | Loại |
|---|---|---|---|---|
| F-01 | **Không dùng thuộc tính nhạy cảm** | Kiểm tra tĩnh: hàm ranking/explanation không nhận tham số hay trường nào ngoài `Profile`; contract test gửi trường lạ thì bị 422 | 0 tham chiếu | Unit + contract |
| F-02 | **Counterfactual invariance** | Với mỗi hồ sơ, đổi `gender`/`region` trong sidecar, giữ nguyên profile → so sánh output | Output giống hệt từng byte (trừ `request_id`) ở 100% hồ sơ | Property test |
| F-03 | **Exposure parity** giữa nhóm nhạy cảm | Với top-k (k=5), tính tỷ lệ xuất hiện mỗi môn trong từng nhóm; so sánh bằng chênh lệch tuyệt đối lớn nhất | ≤ 0.10 khi nhóm sinh độc lập (chênh lệch chỉ do lấy mẫu) | Báo cáo + test có seed |
| F-04 | **Coverage theo `academic_pattern`** | Tỷ lệ hồ sơ có ≥1 môn eligible được gợi ý; số môn khác nhau xuất hiện trong top-k của mỗi nhóm | `has_failed`: ≥ 90% hồ sơ có ≥1 gợi ý, trừ khi catalog thật sự không còn môn eligible (khi đó trả `empty` kèm why-not) | Báo cáo |
| F-05 | **Giải thích công bằng** | Nhóm `has_failed` không nhận lý do mang tính phán xét năng lực; mọi reason code phải nằm trong danh sách ở `RECOMMENDER_DESIGN.md` và có evidence | 0 reason code ngoài danh sách | Unit |
| F-06 | **Độ tập trung (popularity concentration)** | Gini của tần suất xuất hiện các môn trong top-k trên toàn bộ hồ sơ | Theo dõi và báo cáo; cảnh báo nếu > 0.6 | Báo cáo |

F-01, F-02, F-05 là **bắt buộc pass** để release. F-03, F-04, F-06 là chỉ số báo cáo; vượt ngưỡng thì mở ticket điều tra, không tự động chặn release.

## Hiện thực (theo cấu trúc thư mục bắt buộc)

| Thành phần | Đường dẫn | Ticket |
|---|---|---|
| Sinh dữ liệu và nhãn nhóm | `tools/generate_synthetic_data.py` → `tools/out/catalog.json`, `profiles.json`, `cohorts.json` | T-02 |
| Test F-01, F-02, F-05 | `test/backend/test_fairness.py` | T-13 |
| Báo cáo F-03, F-04, F-06 | `tools/fairness_report.py` → `docs/tasks/evidence/fairness-report.md` | T-13 |

## Giới hạn

- Dữ liệu synthetic không phản ánh phân phối thật; pass ở đây chỉ chứng minh **thuật toán không đọc thuộc tính nhóm** và hành vi trên dữ liệu giả lập, không chứng minh công bằng ngoài thực tế.
- Bảng ánh xạ mục tiêu → môn do người viết; thiên lệch trong bảng này (ví dụ gắn một nghề với ít môn) không phát hiện được bằng F-02. Cần review thủ công bảng ánh xạ khi chốt catalog.
