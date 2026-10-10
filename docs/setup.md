# Triển khai AI-07

---

## 1. Thành phần

| Container | Image | Vai trò | Cổng |
| --- | --- | --- | --- |
| `db` | `postgres:16` | Lưu dữ liệu, dùng volume `pgdata` | Không mở ra ngoài |
| `api` | Build từ `build/deploy/Dockerfile` | Phục vụ REST API bằng Uvicorn | `API_BIND`, mặc định `127.0.0.1:8000` |

`api` kết nối tới `db` qua tên service trong network nội bộ của Compose, nên PostgreSQL không cần và không
nên mở cổng ra ngoài máy chủ.

`api` mặc định chỉ lắng nghe trên `127.0.0.1`. Để phục vụ ra internet, đặt một reverse proxy phía trước để
xử lý tên miền, TLS và giới hạn tần suất; phần này nằm ngoài phạm vi repo.

---

## 2. Chuẩn bị máy chủ

```bash
docker --version          # cần Docker Engine
docker compose version    # cần Compose v2
```

Lấy mã nguồn ở một phiên bản xác định, không dùng nhánh đang phát triển:

```bash
git clone <địa chỉ repo> ai-07
cd ai-07
git checkout <tag hoặc commit>
```

---

## 3. Cấu hình

```bash
cp build/deploy/.env.example build/deploy/.env
chmod 600 build/deploy/.env
```

Điền `POSTGRES_PASSWORD` bằng một mật khẩu sinh ngẫu nhiên, và đặt `APP_VERSION` bằng tag hoặc commit đang
triển khai. Các biến còn lại có giá trị mặc định dùng được.

| Biến | Ý nghĩa |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Tài khoản và database được tạo ở lần khởi động đầu tiên của `db` |
| `APP_VERSION` | Nhãn gắn vào tên image `ai07-api`, để biết máy chủ đang chạy phiên bản nào |
| `API_BIND` | Địa chỉ và cổng `api` lắng nghe trên máy chủ |
| `TZ` | Múi giờ của cả hai container |

`.env` không bao giờ được commit; `.gitignore` đã chặn. Mật khẩu không nằm trong image, vì `api` nhận
`DATABASE_URL` qua biến môi trường lúc chạy.

---

## 4. Triển khai lần đầu

Mọi lệnh chạy từ thư mục gốc của repo.

```bash
# 1. Khởi động database và chờ nó sẵn sàng
docker compose -f build/deploy/docker-compose.prod.yml up -d db
docker compose -f build/deploy/docker-compose.prod.yml ps        # chờ trạng thái healthy

# 2. Build image ứng dụng
docker compose -f build/deploy/docker-compose.prod.yml build api

# 3. Tạo lược đồ và nạp dữ liệu
docker compose -f build/deploy/docker-compose.prod.yml run --rm api python -m tools.build_db

# 4. Khởi động API
docker compose -f build/deploy/docker-compose.prod.yml up -d api
```

Bước 3 **xóa và tạo lại toàn bộ bảng** rồi nạp lại từ CSV, nên chỉ chạy khi triển khai lần đầu hoặc khi
cố ý dựng lại dữ liệu. Lệnh in số dòng đã nạp theo từng bảng; đối chiếu con số đó với số dòng trong CSV là
cách kiểm tra nhanh nhất rằng dữ liệu vào đủ.

Nạp riêng dữ liệu chương trình đào tạo, không nạp sinh viên giả lập:

```bash
docker compose -f build/deploy/docker-compose.prod.yml run --rm api python -m tools.build_db --dirs data/seed
```

---

## 5. Kiểm chứng

```bash
docker compose -f build/deploy/docker-compose.prod.yml ps        # cả hai container Up, db healthy
curl -s localhost:8000/v1/health
curl -s localhost:8000/v1/meta
```

`/v1/meta` trả về phiên bản API, phiên bản lược đồ và học kỳ mặc định. So `schema_version` trong phản hồi
với giá trị trong `data/seed/app_settings.csv` của phiên bản đang triển khai: hai giá trị khác nhau nghĩa
là database được nạp bởi một phiên bản mã nguồn khác.

---

## 6. Cập nhật phiên bản

```bash
git fetch && git checkout <tag mới>
# cập nhật APP_VERSION trong build/deploy/.env
docker compose -f build/deploy/docker-compose.prod.yml build api
docker compose -f build/deploy/docker-compose.prod.yml up -d api
```

Cập nhật chỉ thay container `api`; `db` và volume `pgdata` không bị ảnh hưởng. Nếu phiên bản mới đổi lược
đồ hoặc đổi dữ liệu, xem mục 7.

Quay về phiên bản trước: `git checkout` lại tag cũ rồi build và `up -d` như trên. Nếu phiên bản mới đã đổi
lược đồ thì phải nạp lại dữ liệu theo mục 7.

---

## 7. Dựng lại từ đầu

Dựng lại hoàn toàn, xóa sạch dữ liệu:

```bash
docker compose -f build/deploy/docker-compose.prod.yml down -v
docker compose -f build/deploy/docker-compose.prod.yml up -d db
docker compose -f build/deploy/docker-compose.prod.yml run --rm api python -m tools.build_db
docker compose -f build/deploy/docker-compose.prod.yml up -d api
```

---

## 8. Sao lưu và khôi phục

Trong phạm vi hiện tại, **sao lưu định kỳ không phải yêu cầu bắt buộc**: dữ liệu là CSV trong repo và
database dựng lại được bằng một lệnh (mục 7). Cách khôi phục rẻ nhất là nạp lại.

Khi cần bản chụp database — ví dụ để điều tra một sự cố — dùng `pg_dump` trong container:

```bash
docker compose -f build/deploy/docker-compose.prod.yml exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > ai07-$(date +%F).dump
```

Khôi phục từ bản chụp:

```bash
docker compose -f build/deploy/docker-compose.prod.yml exec -T db \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < ai07-2026-10-11.dump
```

Yêu cầu này đổi ngay khi hệ thống bắt đầu lưu dữ liệu không sinh lại được, chẳng hạn khi ghi lịch sử gợi ý
hoặc phản hồi của người dùng.

---

## 9. Log và theo dõi

```bash
docker compose -f build/deploy/docker-compose.prod.yml logs -f api
docker compose -f build/deploy/docker-compose.prod.yml logs --since 1h db
docker compose -f build/deploy/docker-compose.prod.yml ps
```

`db` có healthcheck sẵn trong compose nên trạng thái hiện trực tiếp ở `ps`. Với `api`, dấu hiệu sống là
`/v1/health`; nếu cần theo dõi tự động thì gọi endpoint đó từ bên ngoài theo chu kỳ.

Log ghi ra stdout của container và do Docker quản lý. Nếu máy chủ chạy lâu dài, đặt giới hạn kích thước log
ở mức daemon của Docker để log không chiếm hết đĩa.

---

## 10. Dừng và gỡ bỏ

```bash
docker compose -f build/deploy/docker-compose.prod.yml stop      # dừng, giữ container và dữ liệu
docker compose -f build/deploy/docker-compose.prod.yml down      # xóa container, GIỮ dữ liệu
docker compose -f build/deploy/docker-compose.prod.yml down -v   # xóa container và XÓA dữ liệu
```

---

## 11. Tài liệu liên quan

| Tài liệu | Nội dung |
| --- | --- |
| `README.md` | Bối cảnh, mục tiêu, phạm vi dự án |
| `docs/architecture/README.md` | Kiến trúc và các quyết định kỹ thuật |
| `docs/architecture/api-contract.md` | Hợp đồng API v1 |
| `build/deploy/README.md` | Các file cấu hình triển khai |
| `tools/README.md` | Các script sinh và nạp dữ liệu |
| `test/README.md` | Chạy kiểm thử và môi trường phát triển |
