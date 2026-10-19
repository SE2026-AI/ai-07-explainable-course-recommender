# Hợp đồng API AI-07 — v1

| | |
| --- | --- |
| Phiên bản hợp đồng | 1.0.0 |
| Cập nhật | 2026-10-11 |
| Lược đồ dữ liệu áp dụng | `schema_version = 3.0.0` |

Tài liệu đặc tả giao diện HTTP mà backend cung cấp và các ứng dụng web, di động sử dụng. Backend và
client triển khai độc lập theo tài liệu này.

Các ví dụ dùng dữ liệu của sinh viên `HUS/T03` trong `test/fixtures/students/`.

---

## 1. Nguyên tắc

1. **Phiên bản nằm trong đường dẫn.** Mọi endpoint dưới `/v1`. Trong v1 chỉ được thêm endpoint, thêm
   trường tùy chọn, thêm giá trị enum. Đổi tên, đổi kiểu, bỏ trường hoặc đổi ý nghĩa một trường là thay
   đổi phá vỡ và PHẢI mở `/v2`.
2. **Chỉ dùng mã tự nhiên.** Địa chỉ và JSON dùng `university_code`, `curriculum_code`, `course_code`,
   `student_code`, `term_code`, `block_code`. Khóa chính kiểu số của các bảng là chi tiết nội bộ, thay đổi
   mỗi lần nạp lại dữ liệu, nên KHÔNG ĐƯỢC xuất hiện trong phản hồi.
3. **Mọi tài nguyên của một trường nằm dưới mã trường đó.** Sinh viên, khung chương trình đào tạo,
   học phần và lịch học kỳ đều thuộc về một trường, nên đường dẫn PHẢI có dạng
   `/v1/universities/{university_code}/…`. Riêng với sinh viên, mã sinh viên chỉ duy nhất trong phạm vi
   một trường, nên cặp mã trường + mã sinh viên là bắt buộc để định danh. Mã khung hiện duy nhất toàn hệ
   thống, nhưng vẫn nằm dưới mã trường để các tài nguyên của cùng một trường gom về một nhánh; truy cập
   một mã khung không thuộc trường trong đường dẫn trả về `curriculum_not_found`.
4. **Tên trường JSON là `snake_case` tiếng Anh**, trùng tên cột trong lược đồ PostgreSQL. Tiếng Việt chỉ
   nằm trong các trường dành cho người đọc: `*_name`, `text`, `message`, `note`, `description`.
5. **Không phân trang.** Mỗi endpoint trả về trọn tập kết quả của phạm vi nó mô tả: một khung, một
   sinh viên, hoặc một trường. Client không cần xử lý con trỏ phân trang. Nếu về sau có khung lớn tới mức
   cần chia trang, `limit` và `offset` sẽ được thêm dưới dạng tham số tùy chọn.
6. **v1 chỉ đọc.** Không endpoint nào thay đổi dữ liệu sinh viên. Các endpoint nhận giả định trong body
   tính toán trên bản sao trong bộ nhớ của tiến trình xử lý request.
7. **Tất định.** Cùng tham số PHẢI cho cùng phản hồi, byte-for-byte. Không dùng thời gian hệ thống, không
   dùng số ngẫu nhiên; thứ tự sắp xếp của mọi danh sách được quy định rõ.
8. **Một câu tiếng Việt luôn đi kèm dữ liệu sinh ra nó.** Mỗi trường `text` đều có `code` và `data` cạnh
   nó, đủ để client dựng câu theo cách riêng.

---

## 2. Xác thực và điều kiện sử dụng

v1 không có xác thực, phân quyền hay giới hạn tần suất.

Dữ liệu trong hệ thống là dữ liệu giả lập (`students.is_synthetic = true`). API này KHÔNG ĐƯỢC triển khai
trên dữ liệu sinh viên thật. Việc bổ sung xác thực là thay đổi phá vỡ vì client phải gửi thêm thông tin,
nên sẽ đi cùng `/v2`.

---

## 3. Quy ước chung

### 3.1 Học kỳ

Học kỳ là đơn vị của sản phẩm: câu hỏi hệ thống trả lời là "học kỳ tới nên học gì", và trần tín chỉ cũng
là trần của một học kỳ. Mọi endpoint phụ thuộc vào kết quả học tập đều nhận tham số `term`; client không
gửi thì hệ thống dùng `app_settings.target_term_code`.

`term` quyết định bốn thứ:

1. **Mốc thời gian để xét "đã đạt".** Điều kiện tiên quyết, môn đang nợ và lần học gần nhất của một học
   phần đều tính trên các học kỳ **trước** `term`. Không có mốc này thì không có khái niệm trước – sau,
   nên không xét được tiên quyết.
2. **Vị trí của sinh viên trong lộ trình của khung.** `target_semester` suy ra từ `term` và `cohort_year`;
   đối chiếu nó với `recommended_semester` mới biết một học phần đang đúng kỳ hay đã trễ, là một trong các
   tiêu chí xếp hạng ở mục 4.4.
3. **Xem lại quá khứ và dự tính tương lai.** Cố vấn học tập cần xem tình hình của sinh viên ở một học kỳ
   đã qua; sinh viên cần thử gợi ý cho học kỳ sau nữa. Cùng một sinh viên, hai giá trị `term` cho hai câu
   trả lời khác nhau và cả hai đều đúng.
4. **Tính tất định và khả năng đo.** Nếu hệ thống tự suy "học kỳ hiện tại" theo đồng hồ máy chủ, cùng một
   request sẽ đổi kết quả khi lịch sang kỳ mới, và không đối chiếu được với dữ liệu đăng ký thực tế của
   một học kỳ cụ thể. Tham số tường minh, mặc định lấy từ dữ liệu, giữ cho phản hồi lặp lại được và đo được.

Mỗi trường có lịch học kỳ riêng, nên mã học kỳ PHẢI được tra trong lịch của trường mà tài nguyên thuộc về;
một mã hợp lệ với trường này có thể không tồn tại ở trường khác.

v1 chưa mô hình hóa việc học phần nào được mở ở học kỳ nào, nên `term` không lọc theo khả năng mở lớp.

### 3.2 Kiểu và độ chính xác

| Dữ liệu | Kiểu JSON | Ghi chú |
| --- | --- | --- |
| Tín chỉ | integer | |
| Điểm môn (`score`) | number | Thang điểm của khung, xem `max_score` |
| Điểm trung bình (`gpa`) | number hoặc null | Thang 4, làm tròn 2 chữ số; `null` khi chưa có điểm nào |
| Điểm xếp hạng (`score`, `contribution`) | number | Làm tròn 4 chữ số |
| Mã học kỳ | string | Không phải số, giữ nguyên dạng `"20261"` |
| Trường không áp dụng | vắng mặt | KHÔNG ĐƯỢC trả về `null` cho trường vô nghĩa với ngữ cảnh |

### 3.3 Sắp xếp

| Danh sách | Thứ tự |
| --- | --- |
| Học phần của khung | `sort_no` tăng dần |
| Khối kiến thức | `sort_order` tăng dần |
| Trạng thái học phần | `course_code` tăng dần |
| Gợi ý (`items`) | `score` giảm dần, rồi `recommended_semester` tăng, rồi `course_code` tăng |
| Lý do (`reasons`) | `contribution` giảm dần, rồi `code` tăng |
| Học kỳ | `code` tăng dần |

---

## 4. Từ vựng

### 4.1 Trạng thái một học phần đối với một sinh viên

| `status` | Nghĩa | Có thể được gợi ý |
| --- | --- | --- |
| `passed` | Đã đạt, gồm cả trường hợp được miễn; luôn giữ trạng thái này dù quy tắc khác cũng áp dụng | Không |
| `block_complete` | Môn tự chọn chưa đạt thuộc khối đã tích lũy đủ tín chỉ yêu cầu từ các môn đã đạt trong chính khối đó | Không |
| `missing_prerequisite` | Chưa thỏa ít nhất một nhóm điều kiện tiên quyết | Không |
| `retake` | Đã học, chưa đạt, chưa học lại thành công; chỉ áp dụng khi không có trạng thái ưu tiên cao hơn | Có |
| `eligible` | Chưa học, thỏa mọi nhóm điều kiện tiên quyết và khối tự chọn (nếu có) chưa đủ tín chỉ yêu cầu | Có |

Mỗi học phần của khung có đúng một trạng thái. Tập giá trị này trùng cột `expected_status` trong
`test/fixtures/students/expected_course_status.csv`.

Nếu nhiều quy tắc cùng áp dụng, chọn đúng một trạng thái theo thứ tự ưu tiên:
`passed` > `block_complete` > `missing_prerequisite` > `retake` > `eligible`.
Tín chỉ hoàn thành khối tự chọn chỉ tính tín chỉ của học phần trong khối đó mà sinh viên đã đạt
(bao gồm học phần được miễn). Môn trượt, đang nợ hoặc chỉ đủ điều kiện không được tính. Khi đã đủ
`required_credits`, các học phần còn lại trong khối được gán `block_complete`; học phần đã đạt vẫn là
`passed`. Quy tắc này không áp dụng cho môn ngoài khối tự chọn.

Lược đồ dữ liệu còn hai trạng thái kết quả là `withdrawn` và `in_progress`. Khi dữ liệu có kết quả ở
hai trạng thái này, tập giá trị trên được mở rộng thêm, dưới dạng giá trị enum mới.

### 4.2 Điều kiện tiên quyết

`prerequisite_groups` có kiểu `list[list[string]]`. **Các nhóm nối với nhau bằng VÀ; các mã trong cùng một
nhóm nối với nhau bằng HOẶC.**

```
[["MAT2400"], ["MAT3533"]]      cần MAT2400  VÀ  MAT3533
[["CS101", "MAT2505"]]          cần CS101  HOẶC  MAT2505
```

Một nhóm chỉ có một thành viên là điều kiện bắt buộc. Một học phần có thể có nhiều nhóm, và danh sách
rỗng nghĩa là học phần không có điều kiện tiên quyết.

Client KHÔNG ĐƯỢC làm phẳng cấu trúc hai tầng này thành một danh sách mã, vì làm vậy biến HOẶC thành VÀ.
Một nhóm được thỏa khi ít nhất một mã trong nhóm nằm trong tập môn đã đạt; mọi nhóm đều phải được thỏa.
Danh sách nhóm rỗng luôn được xem là đủ điều kiện.

Điều kiện tiên quyết được xét trên **môn đã đạt ở các học kỳ trước**. Môn đang học hoặc đang nằm trong
cùng một kế hoạch học kỳ không tính là đã đạt. Lược đồ có `requirement_type = corequisite` cho trường hợp
học song hành; v1 chưa xử lý giá trị này.

### 4.3 Mã học phần tiên quyết không thuộc chương trình đào tạo

Văn bản CTĐT có thể dẫn điều kiện tiên quyết bằng mã học phần không nằm trong danh mục học phần của
trường, chẳng hạn mã thuộc một chương trình đào tạo trước đó. Tầng dữ liệu lưu nguyên văn các mã này và
lọc chúng khỏi kết quả truy vấn.

API không trả về các mã này ở bất kỳ endpoint nào. Thông tin về chúng nằm ở `GET /v1/data-issues`.

### 4.4 Mã lý do xếp hạng

| `code` | Nghĩa | Trường trong `data` |
| --- | --- | --- |
| `outstanding_retake` | Môn đang nợ | `term_code`, `score`, `attempt_no` |
| `overdue` | Trễ so với kỳ dự kiến của khung | `recommended_semester`, `target_semester`, `semesters_late` |
| `on_time` | Đúng kỳ dự kiến của khung | `recommended_semester`, `target_semester` |
| `unlocks` | Đạt môn này mở khóa các môn khác | `count`, `course_codes` |
| `strong_topic` | Thuộc chủ đề sinh viên đang học tốt | `topic_code`, `topic_name`, `average_score`, `course_codes` |
| `interest` | Thuộc chủ đề sinh viên tự khai | `topic_code`, `topic_name`, `weight` |

`on_time` và `overdue` loại trừ nhau: một học phần nhận nhiều nhất một trong hai.

Một lý do chỉ xuất hiện khi nó thực sự góp điểm. Tiêu chí không áp dụng thì vắng mặt khỏi `reasons`,
KHÔNG ĐƯỢC trả về với `contribution = 0`.

`strong_topic` tính từ điểm các môn sinh viên đã học, `interest` lấy từ `student_interests`. Kết quả học
tập là tín hiệu chính, khai báo sở thích là tín hiệu phụ; trọng số mặc định phản ánh thứ tự này.

### 4.5 Mã vi phạm kế hoạch học kỳ

| `code` | Nghĩa |
| --- | --- |
| `credit_limit_exceeded` | Tổng tín chỉ vượt `max_credits_per_term` của khung |
| `missing_prerequisite` | Môn chưa đủ điều kiện tiên quyết |
| `already_passed` | Môn sinh viên đã đạt |
| `block_limit_exceeded` | Vượt số tín chỉ cần chọn của một khối tự chọn |
| `duplicate_course` | Một mã môn xuất hiện nhiều lần |
| `not_in_curriculum` | Mã môn không thuộc khung của sinh viên |

---

## 5. Lỗi

Mọi phản hồi mã trạng thái từ 400 trở lên PHẢI có dạng:

```json
{
  "error": {
    "code": "student_not_found",
    "message": "Không tìm thấy sinh viên T99 của trường HUS.",
    "details": {"university_code": "HUS", "student_code": "T99"}
  }
}
```

`code` dành cho máy, `message` dành cho người đọc, `details` là object chứa dữ liệu của lỗi, có thể rỗng.
Yêu cầu này áp dụng cả cho lỗi do tầng validate của web framework sinh ra.

| HTTP | `code` | Trường hợp |
| --- | --- | --- |
| 404 | `university_not_found` | Mã trường không tồn tại |
| 404 | `student_not_found` | Mã sinh viên không tồn tại trong trường đó |
| 404 | `curriculum_not_found` | Mã khung không tồn tại |
| 404 | `course_not_found` | Mã học phần không tồn tại |
| 404 | `term_not_found` | Mã học kỳ không có trong lịch của trường đó |
| 409 | `no_primary_program` | Sinh viên không có CTĐT chính đang hoạt động |
| 422 | `validation_error` | Tham số hoặc body sai kiểu, ngoài khoảng, chứa khóa lạ; `details.fields` liệt kê từng lỗi |
| 500 | `internal_error` | Lỗi không lường trước; `message` không chứa thông tin nội bộ |

---

## 6. Endpoint

| Phương thức | Đường dẫn | Mục đích |
| --- | --- | --- |
| GET | `/v1/health` | Kiểm tra dịch vụ còn sống |
| GET | `/v1/meta` | Phiên bản API, lược đồ, thuật toán; học kỳ mặc định |
| GET | `/v1/universities` | Danh sách trường |
| GET | `/v1/universities/{uni}/terms` | Lịch học kỳ của một trường |
| GET | `/v1/universities/{uni}/curricula` | Danh sách khung CTĐT của một trường |
| GET | `/v1/universities/{uni}/curricula/{curriculum_code}` | Thông tin khung và cây khối kiến thức |
| GET | `/v1/universities/{uni}/curricula/{curriculum_code}/courses` | Học phần của khung |
| GET | `/v1/universities/{uni}/curricula/{curriculum_code}/prerequisite-graph` | Sơ đồ tiên quyết |
| GET | `/v1/universities/{uni}/students/{student_code}/profile` | Tiến độ học tập |
| GET | `/v1/universities/{uni}/students/{student_code}/course-status` | Trạng thái mọi học phần của khung |
| GET | `/v1/universities/{uni}/students/{student_code}/recommendations` | Gợi ý, trọng số mặc định |
| POST | `/v1/universities/{uni}/students/{student_code}/recommendations` | Gợi ý, trọng số tùy chọn và giả định what-if |
| POST | `/v1/universities/{uni}/students/{student_code}/plan-check` | Kiểm tra kế hoạch học kỳ do người dùng chọn |
| GET | `/v1/data-issues` | Các chỗ văn bản gốc mâu thuẫn hoặc thiếu |

### 6.1 `GET /v1/meta`

```json
{
  "api_version": "1.0.0",
  "schema_version": "3.0.0",
  "algorithm": "rule_based_weighted",
  "algorithm_version": "1.0.0",
  "default_term": "20261",
  "curriculum_codes": ["HUS-7460108-2022", "HUS-7480113QTD-2022"]
}
```

`algorithm_version` tăng mỗi khi cách tính điểm hoặc cách dựng lời giải thích thay đổi. Client NÊN hiển
thị giá trị này ở đâu đó trong giao diện để truy được nguyên nhân khi kết quả gợi ý thay đổi.

### 6.2 `GET /v1/universities/{uni}/curricula/{curriculum_code}`

```json
{
  "curriculum_code": "HUS-7480113QTD-2022",
  "university_code": "HUS",
  "major_code": "7480113QTD",
  "major_name": "Khoa học máy tính và thông tin",
  "name": "Chương trình chuẩn",
  "program_type": "standard",
  "effective_from_cohort": 2022,
  "effective_to_cohort": null,
  "total_credits": 129,
  "standard_semesters": 8,
  "max_credits_per_term": 21,
  "pass_score": 4.0,
  "max_score": 10.0,
  "status": "active",
  "blocks": [
    {
      "block_code": "I", "block_name": "Khối kiến thức chung", "parent_block_code": null,
      "selection_rule": "container", "required_credits": 21, "counts_toward_total": true,
      "note": "Chưa tính GDTC, GDQP-AN và Kỹ năng bổ trợ"
    },
    {
      "block_code": "I.2", "block_name": "Ngoại ngữ B1", "parent_block_code": "I",
      "selection_rule": "choose_credits", "required_credits": 5, "counts_toward_total": true,
      "note": "Chọn 1 trong 7 ngoại ngữ"
    }
  ]
}
```

`blocks` là một cây, trả về dạng phẳng kèm `parent_block_code`.

`selection_rule` nhận ba giá trị: `all` (học hết các môn trong khối), `choose_credits` (chọn đủ
`required_credits`), `container` (khối cha, chỉ dùng để nhóm, không chứa học phần trực tiếp).

`counts_toward_total = false` nghĩa là khối không tính vào tổng tín chỉ tốt nghiệp. Client PHẢI tôn trọng
cờ này khi tính và hiển thị tiến độ.

`pass_score` và `max_score` thuộc thang điểm của khung, không phải hằng số toàn hệ thống: mỗi trường có
thang điểm riêng. Client KHÔNG ĐƯỢC viết cứng ngưỡng đạt.

### 6.3 `GET /v1/universities/{uni}/curricula/{curriculum_code}/courses`

```json
{
  "curriculum_code": "HUS-7480113QTD-2022",
  "count": 65,
  "courses": [
    {
      "course_code": "MAT2505",
      "course_name": "Lập trình cơ bản",
      "course_name_en": "Introduction to Programming",
      "credits": 3,
      "teaching_language": "vi",
      "block_code": "III",
      "block_name": "Khối kiến thức theo khối ngành",
      "is_required": true,
      "recommended_semester": 2,
      "prerequisite_groups": [["HUS1011"]],
      "primary_topic": "lap_trinh",
      "topics": ["lap_trinh"],
      "skills": ["lap_trinh"]
    }
  ]
}
```

`is_required = true` khi khối chứa môn có `selection_rule = "all"`.

`recommended_semester` là kỳ dự kiến theo lộ trình của khung, đếm từ 1 đến `standard_semesters`.

### 6.4 `GET /v1/universities/{uni}/students/{student_code}/profile`

Tham số: `term`.

```json
{
  "university_code": "HUS",
  "student_code": "T03",
  "full_name": "Sinh viên test HUS T03",
  "curriculum_code": "HUS-7480113QTD-2022",
  "major_code": "7480113QTD",
  "major_name": "Khoa học máy tính và thông tin",
  "cohort_year": 2025,
  "year_of_study": 2,
  "term": "20261",
  "target_semester": 3,
  "credits_earned": 34,
  "credits_outstanding": 3,
  "total_credits": 129,
  "gpa": 2.76,
  "max_credits_per_term": 21,
  "interests": ["phan_mem"],
  "outstanding_courses": ["MAT2505"],
  "blocks": [
    {"block_code": "I.1", "required_credits": 16, "earned_credits": 8, "counts_toward_total": true},
    {"block_code": "I.2", "required_credits": 5, "earned_credits": 5, "counts_toward_total": true},
    {"block_code": "II", "required_credits": 5, "earned_credits": 2, "counts_toward_total": true},
    {"block_code": "IV", "required_credits": 28, "earned_credits": 13, "counts_toward_total": true},
    {"block_code": "V.1", "required_credits": 49, "earned_credits": 6, "counts_toward_total": true}
  ]
}
```

- `target_semester` = `2 × (year_of_study − 1) + term_no`: thứ tự của học kỳ đang xét trong lộ trình của
  khung. Với `T03` ở kỳ `20261`: `2 × 1 + 1 = 3`.
- `credits_earned` và `credits_outstanding` chỉ tính các khối có `counts_toward_total = true`, và chỉ tính
  lần học gần nhất của mỗi môn.
- `gpa` là `null` khi sinh viên chưa có kết quả nào.
- Endpoint này KHÔNG ĐƯỢC trả về thuộc tính nhạy cảm của sinh viên (`student_attributes`: `fairness_group`,
  `gender`). Dữ liệu đó chỉ phục vụ đánh giá công bằng ngoài luồng xử lý API.

### 6.5 `GET /v1/universities/{uni}/students/{student_code}/course-status`

Tham số: `term`.

Trả về một dòng cho mỗi học phần thuộc khung của sinh viên.

```json
{
  "university_code": "HUS",
  "student_code": "T03",
  "curriculum_code": "HUS-7480113QTD-2022",
  "term": "20261",
  "summary": {"passed": 10, "retake": 1, "eligible": 15, "missing_prerequisite": 33, "block_complete": 6},
  "courses": [
    {
      "course_code": "MAT2505", "course_name": "Lập trình cơ bản", "credits": 3,
      "block_code": "III", "status": "retake",
      "last_attempt": {"term_code": "20252", "attempt_no": 1, "score": 3.0, "letter_grade": "F"},
      "text": "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở học kỳ 20252 (điểm 3,0)."
    },
    {
      "course_code": "MAT3533", "course_name": "Học máy", "credits": 3,
      "block_code": "V.1", "status": "missing_prerequisite",
      "missing_prerequisites": [["MAT2323"]],
      "text": "Chưa học được Học máy: cần hoàn thành Xác suất - Thống kê (MAT2323) trước."
    },
    {
      "course_code": "FLF1207", "course_name": "Tiếng Nga B1", "credits": 5,
      "block_code": "I.2", "status": "block_complete",
      "block": {"block_code": "I.2", "block_name": "Ngoại ngữ B1", "required_credits": 5, "earned_credits": 5},
      "text": "Không cần học Tiếng Nga B1: khối Ngoại ngữ B1 đã đủ 5/5 tín chỉ."
    },
    {
      "course_code": "MAT2323", "course_name": "Xác suất - Thống kê", "credits": 4,
      "block_code": "IV", "status": "eligible",
      "text": "Học được Xác suất - Thống kê: đã đủ điều kiện tiên quyết."
    },
    {
      "course_code": "PHI1006", "course_name": "Triết học Mác - Lênin", "credits": 3,
      "block_code": "I.1", "status": "passed",
      "last_attempt": {"term_code": "20251", "attempt_no": 1, "score": 7.5, "letter_grade": "B"},
      "text": "Đã đạt Triết học Mác - Lênin (điểm 7,5)."
    }
  ]
}
```

Trường chỉ xuất hiện khi có nghĩa với trạng thái: `missing_prerequisites` với `missing_prerequisite`,
`block` với `block_complete`, `last_attempt` với `passed` và `retake`.

Môn được miễn có `status = "passed"`, `last_attempt.score = null` và `last_attempt.letter_grade = null`.

`summary` cộng lại bằng số học phần của khung.

### 6.6 `GET` và `POST /v1/universities/{uni}/students/{student_code}/recommendations`

Hai phương thức trả về cùng một cấu trúc. `GET` dùng trọng số mặc định và không nhận giả định; `POST`
nhận trọng số tùy chọn và giả định what-if.

Tham số `GET`: `term`, `limit`.

Body `POST`:

```json
{
  "term": "20261",
  "limit": 5,
  "weights": {"outstanding_retake": 3.0, "overdue": 2.0, "on_time": 2.0,
              "unlocks": 1.5, "strong_topic": 1.0, "interest": 0.5},
  "assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 6.0}]
}
```

| Trường | Quy định |
| --- | --- |
| `limit` | Mặc định 5, tối đa 20. Ngoài khoảng → `validation_error` |
| `weights` | Gửi một phần được, khóa thiếu lấy mặc định. Giá trị `>= 0`. Khóa lạ → `validation_error` |
| `assumptions` | `status` nhận `passed` hoặc `failed`; `score` trong `[0, max_score]` của khung; `course_code` phải thuộc khung |

Bảng trọng số mặc định chính là bảng trong ví dụ trên.

Giả định trong `assumptions` được áp lên bản sao dữ liệu trong bộ nhớ và KHÔNG ĐƯỢC ghi vào cơ sở dữ liệu.

Phản hồi, rút gọn còn hai học phần:

```json
{
  "university_code": "HUS",
  "student_code": "T03",
  "curriculum_code": "HUS-7480113QTD-2022",
  "term": "20261",
  "algorithm_version": "1.0.0",
  "what_if": false,
  "weights": {"outstanding_retake": 3.0, "overdue": 2.0, "on_time": 2.0,
              "unlocks": 1.5, "strong_topic": 1.0, "interest": 0.5},
  "candidate_count": 16,
  "items": [
    {
      "rank": 1, "course_code": "MAT2505", "course_name": "Lập trình cơ bản", "credits": 3,
      "block_code": "III", "status": "retake", "score": 5.5,
      "reasons": [
        {"code": "outstanding_retake", "contribution": 3.0,
         "text": "Bạn chưa đạt môn này ở học kỳ 20252 (điểm 3,0).",
         "data": {"term_code": "20252", "score": 3.0, "attempt_no": 1}},
        {"code": "unlocks", "contribution": 1.5,
         "text": "Đạt môn này sẽ mở khóa 12 học phần khác của chương trình.",
         "data": {"count": 12, "course_codes": ["MAT1202", "MAT3373E", "MAT3505", "MAT3506", "MAT3507",
                  "MAT3514", "MAT3519", "MAT3539", "MAT3550E", "MAT3554E", "MAT3558", "MAT3560"]}},
        {"code": "overdue", "contribution": 1.0,
         "text": "Môn này dự kiến học ở kỳ 2, bạn đang ở kỳ 3.",
         "data": {"recommended_semester": 2, "target_semester": 3, "semesters_late": 1}}
      ]
    },
    {
      "rank": 2, "course_code": "MAT2323", "course_name": "Xác suất - Thống kê", "credits": 4,
      "block_code": "IV", "status": "eligible", "score": 2.75,
      "reasons": [
        {"code": "on_time", "contribution": 2.0,
         "text": "Đúng kỳ dự kiến của chương trình (kỳ 3).",
         "data": {"recommended_semester": 3, "target_semester": 3}},
        {"code": "unlocks", "contribution": 0.75,
         "text": "Đạt môn này sẽ mở khóa 5 học phần khác của chương trình.",
         "data": {"count": 5, "course_codes": ["MAT3452", "MAT3453", "MAT3533", "MAT3534", "MAT3535"]}}
      ]
    }
  ],
  "not_eligible": [
    {
      "course_code": "MAT3533", "course_name": "Học máy", "credits": 3,
      "status": "missing_prerequisite", "missing_prerequisites": [["MAT2323"]],
      "text": "Chưa học được Học máy: cần hoàn thành Xác suất - Thống kê (MAT2323) trước."
    }
  ]
}
```

Quy định của endpoint này:

1. `items` chỉ chứa học phần có `status` là `retake` hoặc `eligible`, nhiều nhất `limit` phần tử.
   Điều kiện tiên quyết và giới hạn của khối tự chọn là ràng buộc cứng: không giá trị trọng số nào có thể
   đưa một học phần vi phạm vào `items`.
2. `score` PHẢI bằng tổng `contribution` của `reasons`, làm tròn 4 chữ số.
3. `rank` bắt đầu từ 1, liên tục, theo thứ tự ở mục 3.3.
4. `candidate_count` là tổng số học phần có thể gợi ý (`retake` + `eligible`), kể cả phần vượt `limit`.
5. `weights` trong phản hồi là bảng trọng số đã dùng, sau khi ghép giá trị client gửi với giá trị mặc định.
6. `what_if` là `true` khi request có `assumptions` khác rỗng.
7. `not_eligible` liệt kê mọi học phần còn lại của khung kèm lý do, cùng cấu trúc với `courses` ở mục 6.5.
8. Trạng thái của một học phần trong `not_eligible` PHẢI trùng trạng thái mà `GET .../course-status` trả về
   với cùng `term` và cùng `assumptions`.

### 6.7 `POST /v1/universities/{uni}/students/{student_code}/plan-check`

Body:

```json
{"term": "20261", "course_codes": ["MAT2505", "MAT2323", "MAT2503", "PHI1002", "HIS1056", "MAT3533"]}
```

```json
{
  "university_code": "HUS", "student_code": "T03", "term": "20261",
  "total_credits": 18, "max_credits_per_term": 21, "valid": false,
  "violations": [
    {
      "code": "missing_prerequisite", "course_code": "MAT3533",
      "text": "Học máy chưa học được: cần hoàn thành Xác suất - Thống kê (MAT2323) trước.",
      "data": {"missing_prerequisites": [["MAT2323"]]}
    }
  ]
}
```

- `total_credits` chỉ cộng học phần thuộc khối có `counts_toward_total = true`.
- `valid` là `true` khi `violations` rỗng.
- Một học phần có thể sinh nhiều vi phạm.
- Theo mục 4.2, học phần khác trong cùng kế hoạch không được tính là đã đạt khi xét tiên quyết. Trong ví
  dụ trên `MAT3533` vẫn vi phạm dù `MAT2323` có mặt trong kế hoạch.

### 6.8 `GET /v1/data-issues`

```json
{
  "count": 7,
  "issues": [
    {
      "source_code": "QD3568_2023",
      "source_title": "Ban hành CTĐT (điều chỉnh) ngành Khoa học máy tính và thông tin",
      "document_number": "3568/QĐ-ĐHKHTN",
      "entity_type": "prerequisite",
      "entity_key": "*",
      "issue_type": "external_course_code",
      "description": "Một số điều kiện tiên quyết dùng mã không thuộc CTĐT (MAT2301, MAT2303, MAT2311, MAT2316, MAT2318, MAT2319, MAT2321, MAT2406); giữ nguyên văn, không liên kết được",
      "status": "open"
    }
  ]
}
```

`status` nhận `open`, `resolved_in_data`, `closed`.

---

## 7. Bất biến

Những tính chất sau là phần bắt buộc của hợp đồng, kiểm thử tự động cho mọi phiên bản.

| Bất biến | Cách kiểm |
| --- | --- |
| Gợi ý không vi phạm quy chế | Mọi `items[].course_code` có trạng thái `eligible` hoặc `retake` trong `test/fixtures/students/expected_course_status.csv` |
| Trạng thái học phần đúng | So toàn bộ `course-status` với `expected_course_status.csv` |
| Lời giải thích khớp điểm | `score == round(sum(reasons[].contribution), 4)` với mọi phần tử của `items` |
| Lời giải thích không có lý do lạ | Mọi `reasons[].code` có mặt trong `weights` của cùng phản hồi |
| Hai endpoint nhất quán | `not_eligible` trùng phần tương ứng của `course-status` |
| Không phụ thuộc nhóm công bằng | Hai sinh viên giống nhau mọi mặt trừ `fairness_group` nhận cùng danh sách gợi ý |
| Không lộ dữ liệu nhạy cảm | Không phản hồi nào chứa khóa `fairness_group` hoặc `gender` |
| Tất định | Hai lần gọi cùng tham số cho phản hồi giống nhau từng byte |
| Có ích | So `items` với `data/synthetic/course_registrations.csv` của học kỳ tương ứng, đo precision@k |
| Lỗi đúng định dạng | Mọi phản hồi từ 400 trở lên khớp lược đồ ở mục 5 |

---

## 8. Ngoài phạm vi v1

- Xác thực, phân quyền, giới hạn tần suất.
- Endpoint ghi dữ liệu: đăng ký học phần, sửa kết quả học tập, lưu phản hồi của người dùng.
- Phân trang, lọc và sắp xếp tùy ý trên các danh sách.
- Tiếng Anh cho `text` và `message`.
- Lời giải thích do mô hình ngôn ngữ sinh. Nếu dùng về sau, mô hình ngôn ngữ chỉ diễn đạt lại lời giải
  thích đã có và KHÔNG ĐƯỢC tham gia quyết định học phần nào được gợi ý.
- Xếp lịch học, phòng học, dự đoán điểm.
- Lưu lịch sử gợi ý. Lược đồ có `recommendation_runs`, `recommendation_items`, `recommendation_feedback`
  nhưng v1 không ghi vào chúng.

---

## 9. Quản lý thay đổi

1. `docs/api/openapi.json` được sinh từ code và commit vào repo.
2. CI sinh lại file đó và so với bản đã commit; khác nhau thì build thất bại.
3. Thay đổi thêm vào: cập nhật tài liệu này và `openapi.json` trong cùng pull request.
4. Thay đổi phá vỡ: mở `/v2`, giữ `/v1` cho tới khi các client chuyển xong.
5. Client PHẢI bỏ qua trường lạ trong phản hồi.

---

## 10. Việc còn mở

- Công thức tính `contribution` của từng tiêu chí thuộc tầng xếp hạng, không bị hợp đồng này quy định.
  Đổi công thức thì tăng `algorithm_version`. Sẽ đặc tả ở `docs/architecture/ranking.md`.
- Ngưỡng precision@k tối thiểu cho bất biến "Có ích", chốt sau khi có số đo đầu tiên.
- Danh sách học phần được mở theo từng học kỳ. Khi có dữ liệu này, `term` sẽ lọc thêm theo khả năng mở lớp,
  và `course-status` có thêm một trạng thái cho học phần đủ điều kiện nhưng kỳ đó không mở.
- Dạng dữ liệu của `GET /v1/universities/{uni}/curricula/{curriculum_code}/prerequisite-graph`: `nodes` và `edges`
