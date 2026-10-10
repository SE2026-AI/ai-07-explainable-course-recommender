# Build và triển khai

| File | Dùng cho |
| --- | --- |
| `docker-compose.yml` | PostgreSQL trên máy cá nhân khi phát triển và chạy kiểm thử |
| `docker-compose.prod.yml` | Triển khai trên máy chủ: database và API |
| `Dockerfile` | Image chạy API, build từ thư mục gốc của repo |
| `.env.example` | Bản mẫu cấu hình triển khai; trên máy chủ sao chép thành `.env` |

Quy trình triển khai, cập nhật, dựng lại và sao lưu: `docs/setup.md`.

Không commit file `.env` hay bất kỳ mật khẩu nào vào repo. Tài khoản trong `docker-compose.yml` là tài
khoản dùng trên máy cá nhân, cố ý để lộ trong repo và không được dùng cho máy chủ.
