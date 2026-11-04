# Reflection (AI-assisted draft disclosed in AI Usage Log)

Điều làm tôi tin tưởng hơn là chuỗi bằng chứng có thể kiểm tra lại, bắt đầu từ test thất bại trước khi thêm thông báo. Log đỏ cho thấy thiếu chức năng thật, thay vì lỗi import. Khi patch chạy được, test đọc kết quả bằng kết nối SQLite riêng ngay trong sender, nên thứ tự commit trước gửi được kiểm tra trực tiếp. Mutation đổi student_code sang mã trường vẫn trả HTTP200 nhưng bị assertion giá trị cụ thể phát hiện. Điều này thuyết phục hơn một test chỉ kiểm tra status.

Confidence vẫn có giới hạn. Harness dùng Repository giả lập và SQLite, dù gọi logic plan-check thật. Nó chưa chứng minh transaction PostgreSQL, SMTP hay trải nghiệm trình duyệt. Hàng đợi trong bộ nhớ cũng có thể mất thông báo khi tiến trình dừng. Tôi không xem best-effort là bảo đảm giao nhận. Timeout chỉ hiệu lực với sender bất đồng bộ chịu hủy; transport chặn event loop nằm ngoài bằng chứng hiện có.

Đo tải giúp phát hiện điều unit test không thể hiện: phản hồi chậm và có lỗi khóa SQLite. Vì vậy tôi giữ kết quả chưa đạt thay vì chỉ trình bày các test xanh. Ba lần đổi thứ tự chạy giảm nghi ngờ shared state, nhưng chưa loại hết race hiếm. Coverage dòng cao cũng không thay thế thử nghiệm tải hay mutation.

Test tiếp theo có giá trị nhất là chạy cùng kịch bản trên adapter PostgreSQL riêng sau khi nhóm thống nhất endpoint ghi và invariant. Tôi sẽ tiêm lỗi gửi sau commit, đối chiếu dữ liệu trước sau, rồi đo lại một trăm tác vụ với đầu vào lớn. Chỉ khi có bằng chứng đó mới cân nhắc tích hợp vào ứng dụng nhóm.
