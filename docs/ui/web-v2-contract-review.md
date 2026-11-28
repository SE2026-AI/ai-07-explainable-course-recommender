# Review hợp đồng v2 từ phía web (#64 → #65)

Đối chiếu commit `5ee2737` của PR #65, ngày 28/11/2026. Review có AI hỗ trợ; không thay cho xác nhận endpoint thật đã chạy.

§6.1–6.8 đủ để dựng đăng ký/đăng nhập, hồ sơ, thay toàn bộ bảng điểm, đổi mật khẩu và xóa tài khoản. Client gửi `credentials: include` và `Content-Type: application/json`; chỉ `401 unauthenticated` làm mất phiên. `invalid_credentials` khi xác nhận mật khẩu giữ người dùng ở form.

Các điểm cần chốt trước khi đóng băng hợp đồng:

1. Ví dụ §6.9 còn trường `"..."` thay cho phần còn lại của phản hồi v1, nên chưa phải response đầy đủ dùng trực tiếp làm fixture typed. Web đang ghép fixture transcript v1 với phần `graduation_conditions` của ví dụ và ghi rõ tiến trình mock là mẫu cố định. Đề nghị thay bằng ví dụ đầy đủ, giữ nguyên schema.
2. §2.4 nói mọi endpoint khác ngoài register/login đều cần phiên, nhưng §6.3 cho logout khi đã đăng xuất vẫn204. Đề nghị ghi rõ ngoại lệ logout. Web theo §6.3 và không parse JSON của204.
3. §6.7: sau khi xóa bảng điểm rồi đổi khung, `semesters_completed` được giữ hay reset0? Client dùng giá trị server trả; mock tạm reset0 khi đổi khung. Cần chốt semantics cùng #62.

Các JSON block của toàn bộ §6.1–6.15 đã được chép nguyên nội dung sang `src/web/src/api/v2/examples.json`; `v2-contract.test.ts` so từng block với Markdown. Những endpoint dẫn chiếu body/response của mục khác được giữ đúng, không tự tạo thêm ví dụ vào nguồn hợp đồng.

Kiểu TypeScript v2 tách riêng `api/v2/types.ts`, không sửa generated types v1. Khi OpenAPI có `/v2`, đổi các kiểu này sang kiểu sinh tự động và chạy lại tests. Không merge hay tự sửa hợp đồng của Hoàng trong PR web.
