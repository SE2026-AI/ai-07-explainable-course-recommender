# WEB-8: xuất và nhập file bảng điểm, khớp backend hiện có (#39)

Cùng nhánh với WEB-6 và WEB-7 (PR #46).

## Đã làm

- Bước 4 có "Nhập file JSON" và "Xuất file JSON" (`TranscriptEntryPage.tsx`).
  - Xuất: tải về body §6.10 (`semesters_completed`, `results`) theo thứ tự khung. Dòng đã tick mà chưa có
    điểm và chưa "Miễn" không được ghi.
  - Nhập: nhận body §6.10, hoặc file mẫu trong `test/fixtures/transcripts/` (body nằm trong `request`). File
    ghi `curriculum_code` khác khung đang chọn, không phải JSON, hoặc `semesters_completed` ngoài 0–12 thì
    báo lỗi và giữ nguyên bản nháp. Số kỳ trong file khác số kỳ đang chọn thì chuyển `ky` theo file.
  - Bốn file mẫu đều đọc được (test `fromBody đọc được bảng điểm mẫu …`).
- Đối chiếu kiểu khai báo tay trong `api/transcript.ts` với `openapi.json` trên nhánh `feat/api-transcript-plan-check`
  (API-4/5/6, #38, chưa có PR). Các trường server có thể bỏ (`warnings`, `blocks`, `outstanding_courses`, `items`,
  `not_selected`, `not_eligible`, `gpa`, `text`) giờ là tùy chọn, và màn hình coi thiếu là rỗng.

Kiểm tra: `npm test` 103/103; `lint`, `check:api`, `build` qua.

## Tình trạng backend (18/11/2026)

- API-4 (`transcript`), API-5 (`recommendations`), API-6 (`plan-check`) đã có nhánh, đang trả stub; chưa có PR
  vào `main`. `RULES-4` (dựng sinh viên từ bảng điểm) đang ở PR #43.
- Vì vậy chưa chạy `gen:api` được: `check:api` so với `docs/api/openapi.json` của `main`, chưa có ba endpoint.
- Chưa chạy live: máy này không có PostgreSQL và Docker không chạy.

## Còn lại khi backend merge

- `npm run gen:api`, đổi `api/transcript.ts` sang kiểu sinh tự động trong `schema.ts` rồi xóa file.
- Chạy live với bốn bảng điểm mẫu, chụp ảnh luồng đầy đủ.
- API-6 `plan-check` theo bảng điểm chưa có màn hình nào trong #39 dùng tới.
