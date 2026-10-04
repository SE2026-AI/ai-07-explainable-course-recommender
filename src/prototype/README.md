# CourseCompass prototype

Mở `index.html` trực tiếp trong trình duyệt, hoặc chạy từ thư mục này:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Truy cập http://127.0.0.1:8765 . Không cần cài thư viện.

## Luồng dùng thử
1. Chọn mục tiêu; tìm môn; mở bằng chứng và điều kiện.
2. Thêm/bỏ môn; đổi giới hạn tín chỉ. Môn trùng, thiếu tiên quyết hoặc vượt hạn mức bị chặn.
3. Bỏ bộ lọc điều kiện rồi tìm AI301 để xem tình huống thiếu tiên quyết.
4. Chọn lỗi dịch vụ gợi ý: danh sách dự phòng vẫn cho chọn môn, điểm cá nhân hóa được bỏ.
5. Chọn lỗi danh mục: dừng đề xuất mới và giữ kế hoạch trong phiên; dùng nút thử lại để khôi phục.
6. Chuyển màn hình đối tác để xem phản hồi JSON mẫu; tải kế hoạch mẫu.

## Giới hạn
Dữ liệu giả lập; xếp hạng bằng quy tắc; API chỉ là response preview, chưa có backend. Kế hoạch mất khi tải lại trang. CSS có bố cục cho màn hình nhỏ; chưa kiểm chứng với thiết bị di động thật. Chưa đo tải, bảo mật, retention hoặc SLA. Chưa có CI/CD.

## Kiểm tra đã thực hiện
Thử trực tiếp trong trình duyệt: thêm SE201 tăng lên 3 tín chỉ và chặn thêm trùng; chuyển degraded hiện fallback; chuyển unavailable giữ kế hoạch và không trả danh sách mới; thử lại khôi phục danh sách; tìm AI301 khi bỏ bộ lọc hiện thiếu CS202/ST201 và vô hiệu hóa thêm môn. Xuất file và clipboard chưa kiểm tra.
