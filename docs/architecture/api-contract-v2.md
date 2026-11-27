# Hợp đồng API AI-07 — v2

| | |
| --- | --- |
| Phiên bản hợp đồng | 2.0.0 |
| Cập nhật | 2026-11-28 |
| Lược đồ dữ liệu áp dụng | `schema_version = 4.0.0` |
| Issue | #61 (`CONTRACT-2`) |

v2 thêm tài khoản sinh viên: bảng điểm, tiến trình học tập và kế hoạch học kỳ được lưu trên server theo
từng sinh viên, và admin bổ sung được chương trình đào tạo. Logic gợi ý, kiểm tra kế hoạch và câu giải
thích **giữ nguyên** như v1; v2 chỉ đổi chỗ lấy dữ liệu, từ body của request sang dữ liệu đã lưu.

Tài liệu này chỉ ghi những gì **khác** v1. Mọi điều không nhắc tới ở đây theo `api-contract.md` (v1):
hình dạng phản hồi §6.10–6.12, mã lỗi §5, từ vựng §4, quy ước §3.

---

## 1. Nguyên tắc

Nguyên tắc 1–5 và 8 của v1 giữ nguyên. Hai nguyên tắc đổi:

| v1 | v2 |
| --- | --- |
| 6. Chỉ đọc. Không endpoint nào ghi dữ liệu | Endpoint `/v2/me/*` ghi dữ liệu **của chính người đang đăng nhập**. Endpoint `/v2/admin/*` ghi dữ liệu tham chiếu. Không endpoint nào ghi dữ liệu của người khác |
| 7. Tất định byte-for-byte | Vẫn tất định, trừ ba loại trường: thời điểm (`created_at`, `updated_at`, `expires_at`), mã ngẫu nhiên (`user_id`, `undo_token`) và `version` |

Thêm hai nguyên tắc:

9. **`/v1` không đổi.** Đối tác đang dùng `/v1` không phải sửa gì. Danh mục khung, học phần, sơ đồ tiên quyết
   vẫn đọc qua `/v1` và không cần đăng nhập.
10. **Chỉ một trường.** Production chỉ có trường `HUS` (ĐHKHTN – ĐHQGHN), nên đường dẫn `/v2` không có mã trường.
    Mọi `curriculum_code` trong v2 phải là khung của `HUS`.

## 2. Xác thực, phân quyền, quyền riêng tư

### 2.1 Tài khoản

- Sinh viên tự đăng ký bằng email và mật khẩu.
- Email được chuẩn hóa: bỏ khoảng trắng hai đầu, đổi về chữ thường. `SV@HUS.edu.vn` và `sv@hus.edu.vn` là một
  tài khoản. Bản này chưa xác minh email.
- Mật khẩu dài 8–128 ký tự, băm bằng argon2id, không bao giờ trả về hay ghi ra log.
- Hai vai trò: `student` (mặc định khi đăng ký) và `admin`. Không endpoint nào tự cấp quyền admin; admin đầu
  tiên tạo bằng lệnh `python -m tools.create_admin`.
- Quên mật khẩu: admin đặt lại (mục 6.13). Bản này chưa gửi email.

### 2.2 Phiên đăng nhập

- Đăng ký hoặc đăng nhập thành công thì server đặt cookie `ai07_session`: `HttpOnly`, `Secure`,
  `SameSite=Lax`, `Path=/`, sống 7 ngày kể từ lúc đăng nhập.
- Giá trị cookie là chuỗi ngẫu nhiên 32 byte. Database chỉ lưu SHA-256 của chuỗi đó (`sessions.token_hash`), nên
  lộ database không lộ phiên đăng nhập.
- Đăng xuất, đổi mật khẩu hay admin đặt lại mật khẩu đều xóa phiên tương ứng (mục 6.3, 6.6, 6.13).
- Chống CSRF: mọi request ghi dữ liệu (`POST`, `PUT`, `DELETE`) phải có `Content-Type: application/json`, và nếu có
  header `Origin` thì phải trùng nguồn của web. Sai thì `403 forbidden`.

### 2.3 Giới hạn đăng nhập sai

Sai mật khẩu quá **5 lần trong 15 phút** cho cùng một email, hoặc từ cùng một địa chỉ IP, thì `POST
/v2/auth/login` trả `429 too_many_attempts` cho tới khi hết 15 phút, kể cả khi lần sau gõ đúng.
`details.retry_after_seconds` cho biết còn bao lâu. Địa chỉ IP chỉ lưu dạng SHA-256 (`login_attempts.ip_hash`),
và các lần thử cũ hơn một ngày bị xóa.

### 2.4 Phân quyền

| Đường dẫn | Ai gọi được |
| --- | --- |
| `/v1/*` | Mọi người, không cần đăng nhập |
| `POST /v2/auth/register`, `POST /v2/auth/login` | Mọi người |
| Mọi đường dẫn khác dưới `/v2` | Người đã đăng nhập; thiếu hoặc hết hạn cookie → `401 unauthenticated` |
| `/v2/admin/*` | Chỉ `admin`; sinh viên gọi → `403 forbidden` |

`/v2/me/*` luôn là dữ liệu của người đang đăng nhập; không có tham số nào để đọc dữ liệu người khác.

### 2.5 Quyền riêng tư

v2 chạy trên **dữ liệu thật**: sinh viên thật nhập bảng điểm thật. Mục 2 của hợp đồng v1 ("KHÔNG ĐƯỢC triển
khai trên dữ liệu sinh viên thật", "server KHÔNG ĐƯỢC lưu bảng điểm") chỉ áp cho `/v1`. Với `/v2`:

1. Server lưu đúng những gì sinh viên nhập: email, mật khẩu đã băm, khung chương trình, khóa, bảng điểm, kế
   hoạch học kỳ. Không lưu họ tên hay mã sinh viên.
2. Bảng điểm và kế hoạch chỉ dùng để tính phản hồi cho chính sinh viên đó.
3. Log của server không chứa mật khẩu, cookie, bảng điểm hay kế hoạch. Email trong log được che bớt
   (`s***@hus.edu.vn`).
4. `DELETE /v2/me` xóa tài khoản cùng **mọi** dữ liệu của nó trong cùng một transaction.
5. Dữ liệu giả lập (`data/synthetic`, `test/fixtures`) không bao giờ được nạp vào database production.

## 3. Quy ước chung

Như mục 3 của v1, cộng:

- Thời điểm theo ISO 8601, có múi giờ: `"2026-11-30T08:00:00+07:00"`.
- `user_id` là UUID dạng chuỗi. Đây là mã duy nhất của một tài khoản được phép xuất hiện trong API; khóa số
  `users.id` không bao giờ xuất hiện (nguyên tắc 2).
- `semester` là kỳ thứ mấy của sinh viên, từ 1 đến 12, như `results[].semester` của §6.10 v1. Kế hoạch học kỳ
  gắn với `semester`, không gắn với mã học kỳ `term_code`.
- Kỳ kế tiếp là `semesters_completed + 1`. Chỉ kế hoạch của kỳ kế tiếp sửa được; kế hoạch của các kỳ trước
  chỉ đọc.

## 4. Lỗi

Định dạng lỗi như mục 5 của v1. Mã lỗi mới:

| HTTP | `code` | Khi nào | `details` |
| --- | --- | --- | --- |
| 401 | `unauthenticated` | Thiếu cookie, cookie sai hoặc hết hạn | `{}` |
| 401 | `invalid_credentials` | Sai email hoặc mật khẩu. Một câu cho cả hai trường hợp, để không dò được email nào đã đăng ký | `{}` |
| 403 | `forbidden` | Sinh viên gọi `/v2/admin/*`; request ghi dữ liệu không qua được kiểm tra CSRF (mục 2.2) | `{}` |
| 404 | `plan_not_found` | Chưa có kế hoạch cho `semester` đó | `semester` |
| 404 | `user_not_found` | Admin gọi tới `user_id` không có | `user_id` |
| 409 | `email_taken` | Email đã có tài khoản | `{}` |
| 409 | `last_admin` | Admin cuối cùng tự xóa tài khoản của mình (mục 6.5) | `{}` |
| 409 | `profile_required` | Gọi bảng điểm, tiến trình, gợi ý hay kế hoạch khi chưa chọn khung (mục 6.7) | `{}` |
| 409 | `curriculum_not_active` | Chọn khung đang `draft` hoặc `retired` | `curriculum_code`, `status` |
| 409 | `transcript_not_empty` | Đổi khung khi bảng điểm còn kết quả | `results` (số dòng) |
| 409 | `plan_read_only` | Sửa kế hoạch của kỳ đã qua | `semester`, `next_semester` |
| 409 | `plan_version_conflict` | Gửi `version` khác phiên bản hiện tại của kế hoạch (mục 6.10) | `version` (hiện tại) |
| 409 | `undo_unavailable` | Không có thao tác bỏ môn nào hoàn tác được (mục 6.12) | `reason` |
| 409 | `curriculum_exists` | Admin tạo khung trùng mã một khung đã có | `curriculum_code` |
| 409 | `curriculum_not_draft` | Admin sửa hoặc kích hoạt một khung không còn ở `draft` | `curriculum_code`, `status` |
| 422 | `curriculum_invalid` | Gói CTĐT sai luật (mục 6.14) | `errors`: danh sách `{path, message}` |
| 429 | `too_many_attempts` | Đăng nhập sai quá nhiều lần (mục 2.3) | `retry_after_seconds` |

Lỗi đầu vào vẫn là `422 validation_error` với `details.fields` như v1, kể cả lỗi bảng điểm ở mục 6.8 (cùng
đường dẫn trường như §6.10 v1, ví dụ `results[3].score`).

## 5. Danh sách endpoint

| Mục | Phương thức | Đường dẫn | Mô tả |
| --- | --- | --- | --- |
| 6.1 | POST | `/v2/auth/register` | Đăng ký, đăng nhập luôn |
| 6.2 | POST | `/v2/auth/login` | Đăng nhập |
| 6.3 | POST | `/v2/auth/logout` | Đăng xuất |
| 6.4 | GET | `/v2/me` | Tài khoản và hồ sơ của người đang đăng nhập |
| 6.5 | DELETE | `/v2/me` | Xóa tài khoản cùng mọi dữ liệu |
| 6.6 | POST | `/v2/me/password` | Đổi mật khẩu |
| 6.7 | PUT | `/v2/me/profile` | Chọn khung chương trình và khóa |
| 6.8 | GET, PUT | `/v2/me/transcript` | Đọc, lưu bảng điểm |
| 6.9 | GET | `/v2/me/progress` | Tiến trình học tập, kèm điều kiện tốt nghiệp |
| 6.10 | POST | `/v2/me/recommendations` | Gợi ý kỳ kế tiếp từ bảng điểm đã lưu |
| 6.11 | GET, PUT | `/v2/me/plans`, `/v2/me/plans/{semester}` | Kế hoạch học kỳ đã lưu |
| 6.12 | POST | `/v2/me/plans/{semester}/remove`, `.../undo` | Bỏ môn khỏi kế hoạch và hoàn tác |
| 6.13 | GET, POST | `/v2/admin/users`, `/v2/admin/users/{user_id}/reset-password` | Admin tra tài khoản, đặt lại mật khẩu |
| 6.14 | GET, POST, PUT | `/v2/admin/curricula`, `/v2/admin/curricula/{curriculum_code}` | Admin thêm, sửa khung chương trình |
| 6.15 | POST | `/v2/admin/curricula/{curriculum_code}/activate`, `.../retire` | Admin kích hoạt, ngừng một khung |

---

## 6. Endpoint

### 6.1 `POST /v2/auth/register`

```json
{"email": "sv.nguyen@hus.edu.vn", "password": "mat-khau-du-dai"}
```

`201`, đặt cookie `ai07_session` (mục 2.2):

```json
{
  "user": {"user_id": "8f14e45f-ceea-467a-9a45-6d2f3b0e8c11", "email": "sv.nguyen@hus.edu.vn",
           "role": "student", "created_at": "2026-11-30T08:00:00+07:00"}
}
```

Email đã có → `409 email_taken`. Email sai định dạng, mật khẩu ngắn hơn 8 hay dài hơn 128 ký tự →
`422 validation_error` ở `email` hoặc `password`.

### 6.2 `POST /v2/auth/login`

Body như mục 6.1. `200`, đặt cookie, phản hồi như mục 6.1. Sai email hoặc mật khẩu → `401
invalid_credentials`; quá số lần sai → `429 too_many_attempts` (mục 2.3).

### 6.3 `POST /v2/auth/logout`

Body `{}`. `204`, xóa phiên hiện tại và xóa cookie. Gọi khi đã đăng xuất vẫn `204`.

### 6.4 `GET /v2/me`

```json
{
  "user": {"user_id": "8f14e45f-ceea-467a-9a45-6d2f3b0e8c11", "email": "sv.nguyen@hus.edu.vn",
           "role": "student", "created_at": "2026-11-30T08:00:00+07:00"},
  "profile": {"university_code": "HUS", "curriculum_code": "HUS-7480113QTD-2022", "cohort_year": 2024,
              "semesters_completed": 2, "updated_at": "2026-11-30T08:05:00+07:00"}
}
```

`profile` là `null` khi chưa chọn khung. `cohort_year` vắng mặt khi sinh viên không khai (mục 3.2 v1).

### 6.5 `DELETE /v2/me`

```json
{"password": "mat-khau-du-dai"}
```

`204`. Xóa tài khoản, mọi phiên, hồ sơ, bảng điểm, kế hoạch và lịch sử kế hoạch trong một transaction, rồi
xóa cookie. Sai mật khẩu → `401 invalid_credentials`. Admin cuối cùng không tự xóa được tài khoản của mình →
`409 last_admin`.

### 6.6 `POST /v2/me/password`

```json
{"current_password": "mat-khau-du-dai", "new_password": "mat-khau-moi-du-dai"}
```

`204`. Xóa mọi phiên khác của tài khoản, giữ phiên hiện tại. Sai mật khẩu hiện tại → `401
invalid_credentials`.

### 6.7 `PUT /v2/me/profile`

```json
{"curriculum_code": "HUS-7480113QTD-2022", "cohort_year": 2024}
```

`200`, phản hồi là `profile` như mục 6.4.

| Trường | Quy định |
| --- | --- |
| `curriculum_code` | Khung của `HUS`. Không có → `404 curriculum_not_found` (§5 v1). Đang `draft` hoặc `retired` → `409 curriculum_not_active` |
| `cohort_year` | Tùy chọn, số nguyên 2000–2100 |

Đổi sang khung khác khi bảng điểm còn kết quả → `409 transcript_not_empty`: mã học phần của khung cũ không
chắc có trong khung mới, nên sinh viên phải xóa bảng điểm trước (mục 6.8 với `results` rỗng). Gửi lại đúng khung
đang dùng thì chỉ cập nhật `cohort_year`.

### 6.8 `GET` và `PUT /v2/me/transcript`

`PUT` nhận đúng body của §6.10 v1:

```json
{
  "semesters_completed": 2,
  "results": [
    {"course_code": "MAT2400", "semester": 1, "score": 7.5},
    {"course_code": "FLF1107", "semester": 1, "exempted": true},
    {"course_code": "MAT2505", "semester": 2, "score": 3.0}
  ]
}
```

`GET` và `PUT` cùng trả về:

```json
{
  "curriculum_code": "HUS-7480113QTD-2022",
  "semesters_completed": 2,
  "results": [
    {"course_code": "FLF1107", "semester": 1, "exempted": true},
    {"course_code": "MAT2400", "semester": 1, "score": 7.5},
    {"course_code": "MAT2505", "semester": 2, "score": 3.0}
  ],
  "updated_at": "2026-11-30T08:10:00+07:00"
}
```

Quy định:

1. `PUT` thay **toàn bộ** bảng điểm, không cộng dồn. Kiểm tra đúng như §6.10 v1, cùng lỗi và cùng đường dẫn
   trường; sai thì không lưu gì.
2. `results` trả về sắp theo `course_code`.
3. `semesters_completed` lưu trong hồ sơ, nên mục 6.4 trả cùng giá trị.
4. Chưa chọn khung → `409 profile_required`. Chưa lưu bảng điểm lần nào thì `GET` trả `semesters_completed = 0`
   và `results` rỗng, không có `updated_at`.

### 6.9 `GET /v2/me/progress`

Phản hồi của §6.10 v1, tính từ bảng điểm đã lưu, cộng thêm `graduation_conditions`:

```json
{
  "university_code": "HUS",
  "curriculum_code": "HUS-7480113QTD-2022",
  "semesters_completed": 2,
  "target_semester": 3,
  "credits_earned": 24,
  "...": "mọi trường còn lại như §6.10 v1",
  "graduation_conditions": [
    {
      "block_code": "I.3", "block_name": "Kỹ năng bổ trợ", "met": false, "missing_courses": ["HUS1012"],
      "text": "Chưa hoàn thành điều kiện tốt nghiệp Kỹ năng bổ trợ: cần đạt Kỹ năng bổ trợ (HUS1012). Khối này không tính vào 129 tín chỉ tốt nghiệp."
    }
  ]
}
```

| Trường | Quy định |
| --- | --- |
| `graduation_conditions` | Mỗi khối có `counts_toward_total = false` và `selection_rule = all` là một điều kiện tốt nghiệp: phải đạt mọi môn của khối, dù khối không tính vào tổng tín chỉ. Sắp theo `block_code` |
| `met` | `true` khi mọi môn của khối đã đạt hoặc được miễn |
| `missing_courses` | Mã các môn của khối chưa đạt, sắp theo mã; rỗng khi `met = true` |

Bất biến: với cùng `semesters_completed` và `results`, mọi trường chung với §6.10 v1 phải giống hệt phản hồi
của §6.10 v1.

### 6.10 `POST /v2/me/recommendations`

Body là body của §6.11 v1 **bỏ** `semesters_completed` và `results`:

```json
{"min_credits": 15, "max_credits": 20, "skip": ["MAT2503"], "include": ["MAT2407"], "weights": {"unlocks": 2.0}}
```

Phản hồi đúng như §6.11 v1, tính từ bảng điểm đã lưu. Gửi body `{}` thì dùng mọi giá trị mặc định. Server
không lưu lượt gợi ý nào.

### 6.11 Kế hoạch học kỳ: `GET /v2/me/plans`, `GET` và `PUT /v2/me/plans/{semester}`

Một kế hoạch:

```json
{
  "semester": 3,
  "editable": true,
  "version": 2,
  "course_codes": ["MAT2505", "MAT2323", "MAT2503", "PHI1002", "HIS1056", "MAT3533"],
  "min_credits": 20,
  "max_credits": 24,
  "updated_at": "2026-11-30T09:00:00+07:00",
  "check": {
    "total_credits": 17, "max_credits_per_term": 40, "valid": false,
    "violations": ["... như §6.12 v1 ..."],
    "warnings": []
  }
}
```

`GET /v2/me/plans` trả `{"plans": [...]}`, mỗi phần tử như trên nhưng **không** có `check`, sắp theo
`semester` tăng dần. `GET /v2/me/plans/{semester}` trả đúng một kế hoạch kèm `check`; chưa có →
`404 plan_not_found`.

`PUT /v2/me/plans/{semester}` tạo hoặc thay kế hoạch:

```json
{"course_codes": ["MAT2505", "MAT2323"], "min_credits": 15, "max_credits": 20, "version": 2}
```

| Trường | Quy định |
| --- | --- |
| `semester` (đường dẫn) | Phải bằng kỳ kế tiếp. Kỳ đã qua → `409 plan_read_only`. Kỳ sau kỳ kế tiếp → `422 validation_error` ở `semester` |
| `course_codes` | 0–30 mã, mỗi mã một lần, thuộc khung của sinh viên. Mã lặp hoặc không thuộc khung → `422 validation_error` ở `course_codes[i]`. Thứ tự được giữ nguyên |
| `min_credits`, `max_credits` | Tùy chọn, như §6.12 v1, cùng mặc định |
| `version` | Tùy chọn. Gửi thì phải bằng `version` hiện tại, khác → `409 plan_version_conflict`. Dùng để hai tab không ghi đè nhau |

Quy định:

1. Mỗi lần lưu tăng `version` thêm 1, kể cả khi danh sách môn không đổi. Kế hoạch mới tạo có `version = 1`.
   Mọi phiên bản cũ được giữ lại để hoàn tác (mục 6.12).
2. Kế hoạch có vi phạm vẫn được lưu: đó là bản nháp của sinh viên. `check` là phản hồi §6.12 v1 bỏ các trường
   nhận dạng (`university_code`, `curriculum_code`, `target_semester`, `min_credits`, `max_credits`), tính lại
   mỗi lần đọc từ bảng điểm đã lưu.
3. `editable` là `true` chỉ khi `semester` là kỳ kế tiếp. Sau khi sinh viên lưu bảng điểm với
   `semesters_completed` lớn hơn, kế hoạch của các kỳ đã qua chỉ còn đọc.

### 6.12 Bỏ môn và hoàn tác: `POST /v2/me/plans/{semester}/remove`, `POST /v2/me/plans/{semester}/undo`

Chuyển từ VT-097 của v1 (`/v1/universities/{uni}/students/{student_code}/plan/remove`, `.../undo`), giữ nguyên
luật và các ca kiểm thử, thay chỗ lưu và cách xác định người dùng.

`remove`:

```json
{"course_codes": ["MAT2503", "PHI1002"]}
```

`200`:

```json
{
  "plan": {"semester": 3, "editable": true, "version": 3, "course_codes": ["MAT2505", "MAT2323", "HIS1056", "MAT3533"],
           "...": "như mục 6.11, kèm check"},
  "undo": {"undo_token": "u-3c9b0f7e2a41d8c6", "removed_codes": ["MAT2503", "PHI1002"],
           "expires_at": "2026-11-30T09:05:00+07:00"}
}
```

| Trường | Quy định |
| --- | --- |
| `course_codes` | 1–10 mã, mỗi mã một lần, đều đang có trong kế hoạch. Sai → `422 validation_error` ở `course_codes` hoặc `course_codes[i]` |

`undo`:

```json
{"undo_token": "u-3c9b0f7e2a41d8c6"}
```

`200`: `{"plan": {...}, "restored_codes": ["MAT2503", "PHI1002"]}`. Không gửi `undo_token` (body `{}`) thì hoàn
tác lần bỏ môn gần nhất của kế hoạch đó.

Quy định:

1. Mỗi lần `remove` lưu một phiên bản mới của kế hoạch (mục 6.11, quy định 1) và một ảnh chụp hoàn tác. Database
   chỉ lưu SHA-256 của `undo_token`.
2. `undo` khôi phục đúng danh sách môn của phiên bản **trước** lần bỏ môn đó, thành một phiên bản mới, rồi đánh
   dấu ảnh chụp đã dùng.
3. `409 undo_unavailable`, với `details.reason` là một trong:
   - `none`: kế hoạch chưa có lần bỏ môn nào, hoặc `undo_token` không có;
   - `consumed`: ảnh chụp đã hoàn tác rồi; mỗi lần bỏ chỉ hoàn tác được một lần;
   - `expired`: đã quá **300 giây** từ lúc bỏ môn;
   - `plan_changed`: kế hoạch đã được lưu thêm sau lần bỏ môn (`version` hiện tại khác phiên bản ngay sau lần
     bỏ), hoàn tác sẽ xóa mất thay đổi mới.
4. `undo_token` của tài khoản khác được trả `undo_unavailable` với `reason = none`, giống token không tồn tại,
   để không dò được token của người khác. Đây là chỗ đổi so với VT-097 v1 (trả `403`); ca kiểm thử TC-12 đổi
   kết quả mong đợi theo.
5. Không còn trần 24 tín chỉ viết cứng của VT-097: kế hoạch sau khi hoàn tác được kiểm tra bằng `check` như mọi
   kế hoạch (mục 6.11), với trần của khung.
6. Kế hoạch không sửa được (`editable = false`) → `409 plan_read_only` cho cả `remove` và `undo`.

### 6.13 `GET /v2/admin/users`, `POST /v2/admin/users/{user_id}/reset-password`

`GET /v2/admin/users?email=sv.nguyen@hus.edu.vn` trả `{"users": [...]}`, mỗi phần tử là `user` như mục 6.4.
`email` là tham số bắt buộc và phải khớp nguyên văn sau khi chuẩn hóa; không có endpoint liệt kê mọi tài khoản.

`POST .../reset-password`:

```json
{"new_password": "mat-khau-tam-thoi"}
```

`204`. Xóa mọi phiên của tài khoản đó. `user_id` không có → `404 user_not_found`.

### 6.14 Khung chương trình: `GET`, `POST /v2/admin/curricula`, `PUT /v2/admin/curricula/{curriculum_code}`

`GET` trả `{"curricula": [...]}`, mỗi phần tử:

```json
{"curriculum_code": "HUS-7480113QTD-2022", "name": "Chương trình chuẩn", "major_code": "7480113QTD",
 "total_credits": 129, "status": "active", "student_count": 42}
```

`student_count` là số tài khoản đang chọn khung đó, để admin biết trước khi ngừng một khung.

`POST` nhận một **gói CTĐT**: cùng nội dung với các file `curricula.csv`, `curriculum_blocks.csv`, `courses.csv`,
`curriculum_courses.csv`, `prerequisites.csv` của `data/seed`, gom theo một khung:

```json
{
  "curriculum": {
    "curriculum_code": "HUS-7460108-2026", "major_code": "7460108", "major_name": "Khoa học dữ liệu",
    "name": "Chương trình chuẩn", "name_en": "Standard Program", "program_type": "standard",
    "effective_from_cohort": 2026, "total_credits": 127, "standard_semesters": 8,
    "max_credits_per_term": 40, "grading_scheme_code": "HUS_10",
    "source": {"code": "QD1234_2026", "title": "Quyết định ban hành CTĐT ...", "document_number": "1234/QĐ-KHTN",
               "issued_date": "2026-06-30"}
  },
  "blocks": [
    {"block_code": "I", "block_name": "Khối kiến thức chung", "selection_rule": "container",
     "required_credits": 21, "counts_toward_total": true, "sort_order": 1},
    {"block_code": "I.1", "parent_block_code": "I", "block_name": "Học phần bắt buộc khối chung",
     "selection_rule": "all", "required_credits": 16, "counts_toward_total": true, "sort_order": 2}
  ],
  "courses": [
    {"course_code": "PHI1006", "course_name": "Triết học Mác - Lênin", "credits": 3, "block_code": "I.1",
     "sort_no": 1, "recommended_semester": 1, "prerequisites": []},
    {"course_code": "PEC1008", "course_name": "Kinh tế chính trị Mác - Lênin", "credits": 2, "block_code": "I.1",
     "sort_no": 2, "recommended_semester": 2, "prerequisites": [["PHI1006"]]}
  ]
}
```

Quy định:

1. Khung mới luôn ở trạng thái `draft`. Sinh viên không chọn được khung `draft` (mục 6.7).
2. `prerequisites` là các nhóm tiên quyết như §4.2 v1: các nhóm nối bằng VÀ, các mã trong một nhóm nối bằng HOẶC.
3. Học phần dùng chung giữa các khung của trường. Mã đã có thì tên và số tín chỉ phải trùng học phần đã có;
   khác → lỗi ở `courses[i]`. Mã mới thì được tạo.
4. Gói được kiểm tra bằng đúng các luật mà `test/test_reference_data.py` áp cho `data/seed`: tổng tín chỉ bắt
   buộc cộng tín chỉ các khối tự chọn bằng `total_credits`; khối cha bằng tổng khối con tính vào tổng; khối
   `all` bằng tổng tín chỉ môn của nó; học phần chỉ nằm ở khối lá; khối `choose_credits` ghép được đúng
   `required_credits`; tiên quyết không tạo vòng. Sai → `422 curriculum_invalid`, `details.errors` liệt kê mọi
   lỗi, mỗi lỗi một `{"path": "blocks[3].required_credits", "message": "..."}`. Có lỗi thì không lưu gì.
5. Mã khung đã có → `409 curriculum_exists`. Thang điểm phải đã có (`HUS_10`).
6. `PUT /v2/admin/curricula/{curriculum_code}` thay toàn bộ một khung `draft` bằng gói mới, cùng luật. Khung
   không còn `draft` → `409 curriculum_not_draft`: muốn sửa khung đang dùng thì tạo một khung mới với mã mới.

Phản hồi của `POST` và `PUT`: `201` (`200` với `PUT`) với `{"curriculum_code": "...", "status": "draft"}`.

### 6.15 `POST /v2/admin/curricula/{curriculum_code}/activate`, `.../retire`

Body `{}`. `200` với `{"curriculum_code": "...", "status": "active"}` hoặc `"retired"`.

| Thao tác | Từ | Sang | Ghi chú |
| --- | --- | --- | --- |
| `activate` | `draft` | `active` | Kiểm tra lại gói theo mục 6.14, quy định 4 |
| `retire` | `active` | `retired` | Sinh viên đang dùng khung vẫn đọc và lưu được; sinh viên mới không chọn được |

Chuyển trạng thái khác → `409 curriculum_not_draft`.

---

## 7. Bất biến

Bất biến của v1 vẫn áp cho `/v1`. Thêm cho `/v2`:

| Bất biến | Cách kiểm |
| --- | --- |
| Bảng điểm đã lưu tính như §6.10 v1 | Với 4 bảng điểm mẫu của `test/fixtures/transcripts/`: lưu qua mục 6.8, đọc mục 6.9, so mọi trường chung với phản hồi §6.10 v1 cùng body |
| Gợi ý từ bảng điểm đã lưu như §6.11 v1 | Cùng cách, so mục 6.10 với §6.11 v1 |
| Không đọc được dữ liệu người khác | Hai tài khoản A, B: mọi endpoint `/v2/me/*` của A không bao giờ trả dữ liệu của B; `undo_token` của B gửi từ A nhận `undo_unavailable` |
| Xóa tài khoản xóa sạch | Sau `DELETE /v2/me`, mọi bảng người dùng (data-model.md mục 3) không còn dòng nào của tài khoản đó |
| Mật khẩu không lộ | Không phản hồi và không dòng log nào chứa mật khẩu, cookie hay bảng điểm |
| Phiên bản kế hoạch tăng dần | Mỗi lần lưu, `remove`, `undo` tăng `version` đúng 1 |
| Mỗi lần bỏ môn hoàn tác một lần | `undo` lần hai cùng token → `undo_unavailable`, `reason = consumed` |
| Chỉ admin ghi dữ liệu tham chiếu | Mọi `/v2/admin/*` gọi bằng tài khoản `student` → `403 forbidden` |
| Lỗi đúng định dạng | Như v1: mọi phản hồi từ 400 trở lên khớp định dạng mục 5 v1 |

## 8. Dữ liệu

Bảng mới ở `schema_version = 4.0.0`, mô tả đầy đủ ở `data-model.md` mục 3, "Tài khoản và dữ liệu người dùng":
`users`, `sessions`, `login_attempts`, `student_profiles`, `transcript_results`, `study_plans`,
`study_plan_versions`, `plan_undo_snapshots`.

Các bảng này tham chiếu khung và học phần bằng **mã tự nhiên** (`curriculum_code`, `course_code`), không bằng khóa
số, vì khóa số đổi mỗi lần nạp lại dữ liệu tham chiếu. Nạp lại dữ liệu tham chiếu không bao giờ xóa hay đổi bảng
người dùng; lược đồ đổi qua migration (Alembic).

## 9. Ngoài phạm vi v2

- Xác minh email, quên mật khẩu qua email, đăng nhập bằng tài khoản của trường.
- Trường khác ngoài `HUS`.
- Đăng ký học phần thật, xếp lịch học.
- Lưu lịch sử gợi ý; các bảng `recommendation_*` vẫn chưa ghi.
- Sở thích tự khai cho tài khoản (tiêu chí `interest` vẫn vắng mặt như §6.11 v1, quy định 10).

## 10. Quản lý thay đổi

Như mục 9 của v1: `docs/api/openapi.json` sinh từ code, chứa cả `/v1` lẫn `/v2`, CI so với bản đã commit. Sau khi
tài liệu này merge, hình dạng JSON không đổi nữa; thay đổi thêm vào ghi ở đây và tăng phiên bản phụ.
