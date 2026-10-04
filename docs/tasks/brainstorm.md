# Brainstorm — AI-07 / SE2026-T24 / SE.2026.14

## Bài toán và ba hướng sản phẩm
Sinh viên cần chọn môn phù hợp với mục tiêu, kiến thức đã học và quỹ thời gian. Đối tác tích hợp cần phản hồi ổn định, có lý do rõ ràng để hiển thị nhất quán trên web và mobile.

1. **Khám phá theo mục tiêu:** chọn định hướng nghề nghiệp rồi xem môn phù hợp. Dễ bắt đầu, nhưng chưa giải quyết tải học kỳ.
2. **Lập kế hoạch học kỳ có giải thích (chọn để prototype):** đề xuất môn, giải thích bằng dữ liệu môn học, kiểm tra tiên quyết, thêm vào kế hoạch và theo dõi tín chỉ. Có kết quả cụ thể để sinh viên quyết định.
3. **Trợ lý hội thoại:** diễn giải mong muốn tự do. Có ích cho nhu cầu chưa rõ, nhưng tăng chi phí, độ trễ và khó đánh giá. Để sau khi luồng cơ bản được kiểm chứng.

## Giả thuyết cần kiểm chứng
- Sinh viên hiểu lý do đủ để lựa chọn; phỏng vấn 5–8 người và yêu cầu họ giải thích lại đề xuất. Mục tiêu thử nghiệm: ít nhất 80% hiểu đúng lý do và điều kiện tiên quyết.
- Đối tác dùng chung hợp đồng API cho web/mobile; thử tích hợp một màn hình của mỗi nền tảng và kiểm tra xử lý trạng thái normal/degraded/unavailable.
- Các số đo trên là mục tiêu đề xuất, chưa có kết quả nghiên cứu.

## Scope prototype
- Chọn mục tiêu, tải học kỳ; tìm môn và lọc theo điều kiện tiên quyết.
- Xem điểm phù hợp theo quy tắc, bằng chứng, lý do loại môn; thêm/bỏ môn khỏi kế hoạch, tránh trùng và vượt hạn mức.
- Xem JSON phản hồi minh họa; giả lập dịch vụ gợi ý lỗi và mất danh mục.
- Gợi ý lỗi: trả danh sách dự phòng từ danh mục và đánh dấu degraded. Danh mục lỗi: không tạo đề xuất, giữ kế hoạch đang có và cho thử lại.
- Điểm là điểm quy tắc minh họa, không phải xác suất thành công. Prototype chạy tại trình duyệt, chưa gọi API thật.

## Quyết định AI và kiến trúc dự kiến
Augment: sinh viên quyết định đăng ký. Bộ lọc tiên quyết, hạn mức và giải thích cơ bản dùng quy tắc. Chỉ cân nhắc mô hình ngôn ngữ để hiểu mục tiêu tự do hoặc diễn giải nội dung phi cấu trúc sau khi có bộ đánh giá và nguồn dẫn chứng. Đề xuất kiến trúc: web/mobile → API có phiên bản → bộ lọc và xếp hạng → danh mục môn; bộ diễn giải là thành phần tùy chọn và có fallback.

## Rủi ro và bước tiếp theo
Ưu tiên hợp đồng API và tình huống lỗi trước phần trang trí. Chốt schema, mã lỗi, request ID và kiểm thử hợp đồng với đối tác. Lập bộ mẫu có môn thiếu tiên quyết, mục tiêu không khớp, danh mục rỗng, dữ liệu cũ và lỗi thành phần.

Tham số RE-094 (771 người đồng thời, lưu dữ liệu 38 ngày, phản hồi change request trong 10 giờ) là ràng buộc của biến thể bài cá nhân, cần nhóm xác nhận trước khi đưa thành yêu cầu sản phẩm chung. Prototype không chứng minh các tham số này. Nếu được chấp nhận: đo tải 771 người; kiểm tra xóa dữ liệu quá 38 ngày; ghi nhận thời điểm tiếp nhận và phản hồi CR ≤10 giờ. Reliability cần bài thử lỗi thành phần có ngưỡng và môi trường được thống nhất.

## Truy vết dự kiến
| Outcome | Requirement | Acceptance criterion | Planned test |
|---|---|---|---|
| Hiểu đề xuất | Lý do có bằng chứng | Mỗi đề xuất có mục tiêu, điều kiện và mã nguồn danh mục | Kiểm tra phản hồi và phỏng vấn hiểu lý do |
| Kế hoạch khả thi | Kiểm tra tiên quyết và tín chỉ | Không thêm môn chưa đủ điều kiện, trùng hoặc vượt trần | Thử thêm môn ở các ranh giới |
| Tích hợp bền vững | Trạng thái lỗi rõ ràng | Gợi ý lỗi trả degraded có fallback; danh mục lỗi trả unavailable | Tiêm lỗi, kiểm tra schema web/mobile |

## AI Usage
Công cụ: Codex. Prompt người dùng: “mày thử brainstorm vs propotype xem nào”. AI đề xuất và dựng tài liệu, giao diện, dữ liệu mẫu, quy tắc chấm điểm. Các giả thuyết, điểm mẫu và API đều cần nhóm kiểm chứng trước khi dùng trong sản phẩm. Không sử dụng dữ liệu sinh viên thật.
