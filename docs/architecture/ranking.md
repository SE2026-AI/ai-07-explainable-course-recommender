# Xếp hạng và giải thích

Mục 4.4 của `api-contract.md` ghi: **công thức tính `contribution` của từng tiêu chí thuộc tầng xếp
hạng, hợp đồng không quy định**. Tài liệu này là đặc tả của phần đó.

| Nơi | Nội dung |
| --- | --- |
| `src/recommender/scoring.py` | Sáu tiêu chí, mỗi tiêu chí một hàm thuần, không đọc database |
| `src/recommender/selection.py` | Chọn `k` phần tử hoặc chọn trong khoảng tín chỉ, giữ đúng luật khối tự chọn; hàm thuần, không đọc database |
| `src/recommender/__init__.py` | `recommend()`: lấy dữ liệu, gọi sáu tiêu chí, sắp và chọn |
| `test/test_scoring.py` | Công thức từng tiêu chí và hai ví dụ của hợp đồng; không cần database |
| `test/test_selection.py` | Luật khối tự chọn trên các khối thật của khung; không cần database |
| `test/test_recommender_contract.py` | Bất biến của mục 7 trên toàn bộ sinh viên kiểm thử |
| `test/test_transcript_fixtures.py` | Bảng điểm tự nhập của `test/fixtures/transcripts/` và hai ví dụ mục 6.10, 6.11 của hợp đồng |

---

## 1. Điểm của một học phần

Điểm là **tổng `contribution` của các lý do**, làm tròn 4 chữ số (mục 6.6, quy định 2). Mỗi tiêu chí
góp nhiều nhất một lý do, và một lý do chỉ xuất hiện khi nó thực sự góp điểm: tiêu chí không áp dụng
thì vắng mặt khỏi `reasons`, không trả về `contribution = 0` (mục 4.4). Vì vậy trọng số 0 cũng làm
tiêu chí biến mất, không chỉ làm nó vô hại.

Mọi `contribution` có dạng **trọng số × mức độ**, trong đó mức độ nằm trong `[0, 1]`. Hệ quả: điểm tối
đa của một học phần bằng tổng các trọng số áp dụng được, và đổi trọng số không bao giờ làm đổi dấu của
một tiêu chí. `on_time` và `overdue` loại trừ nhau nên điểm tối đa trên thực tế là
`3,0 + 2,0 + 1,5 + 1,0 + 0,5 = 8,0`.

Chỉ học phần có trạng thái `retake` hoặc `eligible` được xếp hạng. Điều kiện tiên quyết và luật khối tự
chọn là **ràng buộc cứng**: `src/rules/status.py` loại môn chưa đủ tiên quyết và khối đã đủ tín chỉ trước
khi tầng này chạy, rồi `src/recommender/selection.py` giữ cho các môn được chọn không làm hỏng khối (mục 5).
Không giá trị trọng số nào đưa được một học phần vi phạm vào danh sách (mục 6.6, quy định 1).

## 2. Bảng trọng số mặc định

Lấy nguyên từ mục 6.6 của hợp đồng; `src/recommender/scoring.py` khai báo lại trong `DEFAULT_WEIGHTS`.

| `code` | Trọng số mặc định |
| --- | --- |
| `outstanding_retake` | 3,0 |
| `overdue` | 2,0 |
| `on_time` | 2,0 |
| `unlocks` | 1,5 |
| `strong_topic` | 1,0 |
| `interest` | 0,5 |

Client gửi một phần bảng cũng được: khóa thiếu lấy mặc định, khóa lạ hoặc giá trị âm làm `recommend()`
raise `ValueError`, và tầng API chuyển thành `validation_error` (mục 5).

Thứ tự của bảng không phải tình cờ. Môn đang nợ nặng nhất vì nó chặn tiến độ tốt nghiệp. Hai tiêu chí
tiến độ đứng ngay sau. `unlocks` là tiêu chí cấu trúc, đứng dưới tiến độ. Hai tiêu chí cuối nói về nội
dung học phần, và **`strong_topic` luôn nặng hơn `interest`**: kết quả học tập là tín hiệu chính, lời
tự khai là tín hiệu phụ (mục 4.4). Đảo hai số này là đổi bản chất sản phẩm, không phải chỉnh tham số.

## 3. Công thức từng tiêu chí

`w` là trọng số của chính tiêu chí đó trong bảng đã ghép.

| Tiêu chí | `contribution` | Khi nào vắng mặt |
| --- | --- | --- |
| `outstanding_retake` | `w` | Học phần không đang nợ |
| `on_time` | `w` | `recommended_semester ≠ target_semester` |
| `overdue` | `w × min(1, semesters_late / 2)` | Không trễ, hoặc khung dự kiến ở kỳ muộn hơn |
| `unlocks` | `w × min(1, count / 10)` | Không học phần nào của khung lấy môn này làm tiên quyết |
| `strong_topic` | `w × (average_score − pass_score) / (max_score − pass_score)` | Không có chủ đề chính, chưa có điểm nào thuộc chủ đề, hoặc điểm trung bình không vượt điểm đạt |
| `interest` | `w × student_interests.weight` | Sinh viên không khai chủ đề của học phần |

### 3.1 Môn đang nợ

Môn đang nợ luôn góp **đủ** trọng số, không chia mức độ theo số lần đã học hay số kỳ đã nợ: nợ một kỳ
hay ba kỳ thì đều phải xử lý ngay. Số lần học nằm trong `data.attempt_no` để người đọc tự thấy mức độ.
`data.score` vắng mặt khi lần học gần nhất không có điểm (mục 3.2).

### 3.2 Đúng kỳ và trễ kỳ

Vị trí của sinh viên trong lộ trình của khung:

```
target_semester = 2 × (year_of_study − 1) + term_no
```

`year_of_study` do `repo.students()` tính sẵn từ `cohort_year` và năm học của học kỳ cần gợi ý; `term_no`
lấy từ lịch của chính trường đó (mục 3.1). Kỳ hè (`term_no = 3`) rơi vào cùng ô với kỳ 1 của năm sau;
v1 không gợi ý cho kỳ hè nên chưa tách riêng.

So sánh với `recommended_semester` của học phần cho ba trường hợp, và **chỉ trường hợp giữa và trường
hợp trái mới sinh lý do**:

| | Lý do |
| --- | --- |
| Khung dự kiến **trước** kỳ hiện tại | `overdue`, mức độ theo số kỳ trễ |
| Khung dự kiến **đúng** kỳ hiện tại | `on_time`, đủ trọng số |
| Khung dự kiến **sau** kỳ hiện tại | không có lý do nào |

Trường hợp thứ ba là lý do một sinh viên kỳ 5 nhận toàn môn bắt buộc của kỳ 5 trước, rồi mới đến môn tự
chọn của kỳ 6, 7. Đó là hành vi đúng, không phải thiếu sót.

Trễ từ **2 kỳ** trở lên là đạt trần: trễ 2 kỳ là trễ một năm học, đã đủ để tiêu chí này nói hết điều nó
có thể nói. Lấy mốc cao hơn sẽ làm một môn trễ 4 kỳ đè bẹp mọi tiêu chí khác.

### 3.3 Mở khóa môn khác

`count` là số học phần **của khung** có môn đang xét nằm trong `prerequisite_groups`, không trừ môn sinh
viên đã đạt. Con số trả lời câu hỏi "môn này nằm ở đâu trong khung", là tính chất của chương trình chứ
không của một sinh viên — và nhờ vậy nó giống nhau với mọi sinh viên cùng khung, dễ đối chiếu khi gỡ lỗi.
Mốc đạt trần là **10 học phần**.

`course_codes` sắp tăng dần theo mã để phản hồi lặp lại được từng byte (bất biến "Tất định", mục 7).

### 3.4 Chủ đề học tốt

`average_score` là điểm trung bình **lần học gần nhất của mọi học phần có điểm** thuộc chủ đề chính đó,
kể cả môn chưa đạt: điểm đo năng lực ở chủ đề, không đo chuyện đã qua môn hay chưa. Môn được miễn không
có điểm nên không tính.

Chuẩn hóa về `[0, 1]` theo thang điểm của khung (`grading_schemes.pass_score` và `max_score`): đúng điểm
đạt là 0, điểm tối đa là 1. Vì vậy sinh viên vừa đủ điểm đạt ở một chủ đề **không** nhận lý do này, và
công thức không phụ thuộc vào việc khung dùng thang 10 hay thang khác.

Một học phần chỉ xét **chủ đề chính** (`course_topics.is_primary`), không xét chủ đề phụ: mỗi học phần có
đúng một chủ đề chính, nên mỗi học phần nhận nhiều nhất một lý do `strong_topic` và `data.topic_code` là
một giá trị đơn, đúng như mục 4.4.

### 3.5 Sở thích tự khai

`student_interests.weight` nằm trong `(0, 1]` với 1 là sở thích chính, nên `contribution` tối đa là 0,5 —
đúng một nửa mức tối đa của `strong_topic`. Đây là tiêu chí duy nhất lấy từ lời khai của sinh viên, và
nó không bao giờ được là tiêu chí quyết định.

## 4. Kiểm chứng với hai ví dụ của hợp đồng

Mục 6.6 có hai học phần kèm điểm, là hai phần tử đầu của gợi ý thật cho sinh viên kiểm thử `HUS/T03`.
`test/test_scoring.py` kiểm lại từng dòng dưới đây bằng hàm thuần, và
`test/test_recommender_contract.py` kiểm cả hai phần tử khớp nguyên văn ví dụ khi chạy `recommend()` trên
dữ liệu kiểm thử:

| Học phần | Lý do | Mức độ | `contribution` |
| --- | --- | --- | --- |
| MAT2505 | `outstanding_retake` | đang nợ từ kỳ 20252 | 3,0 |
| | `unlocks` | `min(1, 12/10) = 1` | 1,5 |
| | `overdue` | `min(1, 1/2) = 0,5` | 1,0 |
| | `strong_topic` | `(5,25 − 4) / (10 − 4) = 0,2083` | 0,2083 |
| | **tổng** | | **5,7083** |
| MAT2323 | `on_time` | kỳ 3, đúng kỳ | 2,0 |
| | `unlocks` | `min(1, 5/10) = 0,5` | 0,75 |
| | `strong_topic` | `(7,5 − 4) / (10 − 4) = 0,5833` | 0,5833 |
| | **tổng** | | **3,3333** |

Bản trước của ví dụ thiếu hai dòng `strong_topic`, nên ghi tổng 5,5 và 2,75 — đúng số học, nhưng không
phải điều hệ thống thật sự trả về cho T03.

## 5. Sắp xếp, trần khối tự chọn và chọn `k` phần tử

`reasons` sắp theo `contribution` giảm dần rồi `code` tăng dần; `items` sắp theo `score` giảm dần, rồi
`recommended_semester` tăng, rồi `course_code` tăng (mục 3.3). Học phần khung không ghi kỳ dự kiến xếp
sau cùng trong nhóm bằng điểm. Ba mốc so sánh này đủ để không còn chỗ nào phụ thuộc thứ tự dòng của
database, nên hai lần gọi cùng tham số cho phản hồi giống nhau từng byte.

Sau khi sắp, `recommend()` đi từ trên xuống và **nhận** một học phần thuộc khối tự chọn chỉ khi cả hai điều
sau cùng đúng, tính cả tín chỉ đã đạt và tín chỉ của những môn cùng khối vừa được chọn ở trên:

1. khối không vượt `required_credits`;
2. phần còn thiếu vẫn ghép được **đúng** bằng các môn chưa đạt, chưa được chọn của khối — kể cả môn chưa
   đủ tiên quyết, vì khối có thể hoàn thành bằng chúng ở các kỳ sau.

Tín chỉ đã đạt của mỗi khối lấy từ `rules.elective_credits_passed()`, chính phép tính quyết định trạng
thái `block_complete`. Điều 1 là `rules.fits_in_block()`, luật "vượt khối" mà tầng luật công bố cho các tầng
khác. Nhờ vậy `recommend()` không thể hiểu "đủ khối" hay "vượt khối" khác tầng luật. Điều 2 chỉ có ở tầng xếp hạng: một kế hoạch làm
khối kẹt lại chưa vi phạm luật nào, nhưng gợi ý nó thì sinh viên không đi tiếp được.

Lý do của điều 2: khối `choose_credits` phải chọn đúng `required_credits` chứ không phải tối thiểu (mục
6.2 của hợp đồng). Khối `II` cần 5 tín chỉ gồm môn 2 và 3 tín chỉ. Nhận một môn 2 rồi thêm một môn 2 nữa
thì chưa vượt, nhưng còn thiếu 1 mà không môn nào đủ nhỏ, nên khối không bao giờ hoàn thành đúng được. Bản
1.0.0 chỉ dừng khi khối đã đủ. Với `k = 20`, nó làm hỏng khối tự chọn của 52/200 sinh viên trong
`data/synthetic`, trong đó 42 em nhận 2 + 2 + 3 = 7/5 tín chỉ ở khối `II`. Bản 1.0.1 gợi ý 2 + 3 và không
làm hỏng khối nào.

Môn học lại (`retake`) cũng theo luật này: trượt một môn tự chọn không buộc phải học lại đúng môn đó, nếu
môn khác trong khối hoàn thành khối đúng hơn. Môn đó vẫn mang trạng thái `retake` trong `course-status`.

Chọn đi từ trên xuống, không tìm tổ hợp tối ưu, để lời giải thích luôn nói được: "môn này không được gợi
ý vì các môn xếp trên nó đã chiếm chỗ trong khối". Điều 2 làm việc này an toàn: cách tham lam có thể chọn
một tổ hợp điểm thấp hơn tổ hợp tốt nhất, nhưng không bao giờ chọn một tổ hợp mà sinh viên không đi tiếp
được.

### 5.1 Phản hồi của `recommend()`

`recommend()` trả về phần của phản hồi mục 6.6 do tầng xếp hạng quyết định, theo đúng thứ tự khóa ở đó:

| Khóa | Nội dung |
| --- | --- |
| `what_if` | `true` khi `assumptions`, `skip` hoặc `swap` khác rỗng |
| `weights` | Bảng trọng số đã ghép với mặc định (mục 2) |
| `candidate_count` | Mọi học phần `retake` + `eligible`, đếm **trước** luật khối tự chọn và trước khi cắt `k` |
| `items` | Các phần tử đã chọn, sắp theo mục 5 |
| `not_eligible` | Mọi học phần còn lại của khung (`passed`, `block_complete`, `missing_prerequisite`), cùng dạng một dòng `course-status`, sắp theo `course_code` |

`not_eligible` dựng từ đúng kết quả `rules.course_status_details()` mà `recommend()` dùng để chọn ứng viên,
cộng câu `text` của `src/explain/`. Tầng xếp hạng không tự tính lại trạng thái hay chi tiết nào, nên
`candidate_count` cộng số phần tử của `not_eligible` luôn bằng số học phần của khung.

Giới hạn hiện tại: tầng luật đọc `last_attempt` từ database chứ chưa từ dòng sinh viên. Với giả định what-if
`passed`, dòng `not_eligible` của môn đó vẫn mang lần học thật, chưa mang lần học giả định.
`test_an_assumed_pass_shows_the_assumed_attempt_in_not_eligible` đánh dấu `xfail` cho tới khi tầng luật sửa.

Dòng sinh viên phải được đọc ở cùng học kỳ với `term_code`, tức `repo.student(uni, code, term_code)`. Lần
học gần nhất của mỗi môn lấy từ cột `latest_attempts` của chính dòng đó, nên lý do `outstanding_retake`, các
môn đã đạt và trạng thái học phần luôn nhìn cùng một mốc thời gian (mục 3.1 của hợp đồng).

### 5.2 Giả định what-if

`src/recommender/whatif.py` áp các giả định lên một **bản sao** của dòng sinh viên, không đọc và không ghi
database. Mỗi giả định được coi là lần học mới nhất của môn đó:

- diễn ra ở học kỳ chính ngay trước học kỳ đang gợi ý — kỳ hè bị bỏ qua, như mục 3.2;
- là lần học thứ `n + 1` nếu môn đã từng học `n` lần;
- `passed` đưa môn vào danh sách đã đạt và xóa khỏi danh sách đang nợ, `failed` làm ngược lại;
- `score` có thể vắng mặt; khi đó môn không góp vào điểm trung bình của tiêu chí `strong_topic`.

Bản sao chỉ đổi những cột mà tầng luật và tầng xếp hạng đọc. Tín chỉ tích lũy và GPA giữ nguyên, nên
không dùng bản sao để dựng `profile`. Giả định sai — mã không thuộc khung, trạng thái lạ, điểm ngoài
`[0, max_score]` của khung, một môn được giả định hai lần, khóa lạ — làm hàm raise `ValueError` với thông
điệp mở đầu bằng đường dẫn tới trường sai, để tầng API đưa vào `details.fields`.

### 5.3 Chưa học một môn và đổi môn

`skip` (chưa muốn học môn này ở học kỳ đang gợi ý) và `swap` (đổi một môn lấy môn khác) không đổi điểm hay
trạng thái của học phần nào. Chúng chỉ đổi bước chọn `k` phần tử của mục 5, sau khi đã áp `assumptions`:

- môn trong `skip` và `swap[].course_code` bị loại khỏi danh sách đã xếp hạng, nên môn xếp kế tiếp lên thế chỗ;
- môn `swap[].replacement` được `pick_items()` xét **trước** mọi môn khác, nên luôn có chỗ và chiếm tín chỉ
  khối tự chọn trước các môn xếp trên nó; danh sách trả về vẫn sắp theo mục 5, nên môn chọn thay đứng ở vị
  trí đúng với điểm của nó, không nhất thiết ở chỗ của môn bị đổi;
- luật khối vẫn áp cho môn chọn thay: nếu nó làm khối không còn hoàn thành đúng số tín chỉ được thì
  `recommend()` raise `ValueError` chỉ vào `swap[i].replacement`, chứ không lặng lẽ bỏ nó đi.

Môn chọn thay giữ nguyên `reasons` thật của nó, kể cả khi điểm thấp: lời giải thích nói vì sao môn đó tốt
hay không tốt, còn việc nó có mặt là do sinh viên chọn — client đã biết điều đó vì chính nó gửi `swap`.
Mọi kiểm tra đầu vào nằm ở `whatif.check_choices()`: mã phải thuộc khung, đang là `retake` hoặc `eligible`,
không lặp lại trong `skip` và `swap`, và số môn chọn thay không vượt `k`.

### 5.4 Chọn trong khoảng tín chỉ

Mục 6.11 của hợp đồng chọn theo tín chỉ thay cho `k`: sinh viên đặt `min_credits` và `max_credits`.
`recommend()` nhận hai tham số này (hoặc một, đầu kia lấy mặc định) thì gọi `pick_within_credits()` thay cho
`pick_items()`. Điểm, `reasons` và thứ tự xếp hạng không đổi gì; chỉ bước chọn khác:

- đi từ trên xuống danh sách đã xếp hạng, nhận một môn khi tổng tín chỉ vẫn không vượt `max_credits` **và**
  hai điều kiện khối tự chọn của mục 5 vẫn đúng;
- môn không vừa thì bỏ qua và **xét tiếp**, không dừng: còn trống 2 tín chỉ thì môn 2 tín chỉ xếp dưới vẫn
  vào được. Đây là chỗ khác `pick_items()`, vốn chỉ dừng khi đủ `k`;
- mỗi môn học được mà không vào `items` có đúng một lý do, xét theo thứ tự `skipped`, `block_full`,
  `credit_budget` (mục 4.6 của hợp đồng). Luật khối xét trước ngân sách tín chỉ, vì môn làm hỏng khối thì
  không có ngân sách nào cứu được;
- `data` của `block_full` và `credit_budget` tính trên kết quả **cuối cùng**. Tín chỉ chỉ tăng dần trong lúc
  chọn, nên môn đã không vừa lúc được xét thì cũng không vừa với danh sách sau cùng, và câu `text` nói đúng
  về chính danh sách sinh viên đang xem.

`min_credits` không bao giờ được đạt bằng cách phá ràng buộc cứng. Khi đã xét hết mà tổng vẫn thấp hơn,
`recommend()` thêm cảnh báo `below_min_credits` chứ không thêm môn. Ở hướng ngược lại, không cần kiểm "tổng
có thể cao hơn không": môn nào còn trong `not_selected` với lý do `credit_budget` đều có `credits` lớn hơn
phần tín chỉ còn trống.

Mức sàn thật là `min(min_credits, credits_to_graduate)`, với `credits_to_graduate` = `total_credits` của khung trừ
`credits_earned` (`rules.plan.credits_to_graduate()`). Sinh viên kỳ cuối còn 7 tín chỉ để tốt nghiệp không thể, và
không cần, học đủ 10: bản 1.1.0 vẫn cảnh báo họ, dù danh sách 7 tín chỉ đó là đúng thứ họ cần. Khi
`credits_to_graduate < min_credits`, `credit_window` mang thêm số đó để câu `text` nói được vì sao.

Câu cảnh báo `below_min_credits` nói đúng nguyên nhân, vì mỗi nguyên nhân có một việc khác nhau để làm
(`_shortfall_cause()`), xét theo thứ tự:

| `cause` | Khi nào | Sinh viên làm gì |
| --- | --- | --- |
| `skipped` | Có môn trong `not_selected` với lý do `skipped` | Bỏ bớt môn khỏi danh sách "chưa học kỳ này" |
| `limits` | Có môn với lý do `credit_budget` hoặc `block_full` | Nới `max_credits`, hoặc chấp nhận |
| `no_more_courses` | Mọi môn học được đã nằm trong `items` | Không làm gì được: kỳ này hết môn học được |

Bản 1.1.0 luôn nói "không còn môn học được nào vừa với mức tối đa và luật khối tự chọn", kể cả khi sinh viên tự
bỏ qua 20 môn vừa, hay khi kỳ đó không còn môn nào học được.

Mặc định là 10–20 tín chỉ. Sàn 10 là của sản phẩm, đặt ở `MIN_CREDITS_FLOOR`; trần là `max_credits_per_term`
của từng khung (HUS 40, DEMO 12), không phải hằng số. Mặc định 20 là lựa chọn của nhóm, chưa dựa trên số
đo nào: đủ cho 6–7 môn, và sinh viên nâng được tới trần của khung. Mặc định của `max_credits` không bao giờ
vượt trần, nên khung DEMO không gửi `max_credits` thì là 12; lỗi chỉ báo ở trường người gọi đã gửi, như
`min_credits` vượt trần.

`skip` và `include` thay cho `skip` và `swap` của mục 5.3. Môn trong `skip` vẫn nằm trong danh sách xếp
hạng, chỉ không bao giờ được nhận, để `not_selected` giữ đúng thứ tự. Môn trong `include` được xét trước mọi
môn khác như `swap[].replacement`; nếu chính các môn `include` làm hỏng khối hoặc cộng lại vượt
`max_credits` thì `recommend()` raise `ValueError` chỉ vào `include[i]`. `swap` không dùng cùng khoảng tín chỉ:
đổi một môn chính là `skip` môn đó và `include` môn kia.

Dòng sinh viên dựng từ bảng điểm tự nhập (mục 6.10 của hợp đồng) khác dòng đọc từ database ở ba chỗ, và
`recommend()` đọc được cả hai:

- `target_semester` có sẵn (`semesters_completed + 1`), nên không tính từ `year_of_study` và học kỳ;
- `latest_attempts` ghi `semester` thay cho `term_code` và `attempt_no`, nên lý do `outstanding_retake` nói
  "ở kỳ 2" thay cho "ở học kỳ 20252";
- `student_id` là `None`, nên không có sở thích tự khai và không có lý do `interest`. Phải chặn trước khi
  gọi `repo.student_interests()`: với `None`, truy vấn đó trả sở thích của mọi sinh viên.

## 6. Những quyết định có thể bàn lại

Năm chỗ dưới đây có lựa chọn khác cũng hợp lý. Đổi chúng thì phải tăng `ALGORITHM_VERSION`.

| Chỗ | Hiện tại | Lựa chọn khác |
| --- | --- | --- |
| `unlocks` | Đếm trên khung | Chỉ đếm môn sinh viên chưa đạt — sát với "mở khóa cho tôi" hơn, nhưng con số đổi theo từng sinh viên |
| `strong_topic`, `interest` | Chỉ xét chủ đề chính | Xét cả chủ đề phụ, lấy chủ đề có trọng số cao nhất |
| Mốc đạt trần | 10 học phần, 2 học kỳ | Chuẩn hóa theo giá trị lớn nhất trong chính khung |
| Khối tự chọn | Tham lam từ trên xuống, giữ khối hoàn thành đúng được | Tối ưu tổ hợp theo tổng điểm |
| Khoảng tín chỉ | Tham lam từ trên xuống, môn không vừa thì xét tiếp (mục 5.4) | Tối ưu tổ hợp để tổng tín chỉ sát `max_credits` hơn |

Chưa có mốc nào trong bảng này được chọn bằng số đo. Bất biến "Có ích" (mục 7 của hợp đồng) giờ đã có
ngưỡng precision@5 ≥ 0,85, đo trên 200 sinh viên của `data/synthetic` sinh với trần 40 tín chỉ mỗi kỳ:

| Phiên bản | precision@5 | precision@10 |
| --- | --- | --- |
| 1.0.0 | 0,8890 | 0,5620 |
| 1.0.1 | 0,8900 | 0,5625 |
| 1.1.0 | 0,8900 | 0,5625 |
| 1.1.1 | 0,8900 | 0,5625 |

precision@10 thấp vì mỗi sinh viên chỉ đăng ký trung bình 6,2 môn, nên trần của nó khoảng 0,62. Đăng ký dự
kiến được sinh theo lộ trình chuẩn của khung — môn nợ trước, rồi môn đúng hoặc trễ kỳ — trùng ba tiêu chí
nặng nhất ở mục 2, nên con số này chỉ dùng để chống thụt lùi, chưa đủ để chọn giữa các phương án trong
bảng. Muốn so các phương án cần một thước đo không dựng từ chính các tiêu chí đó.

## 7. Phiên bản

`src/recommender/__init__.py` công bố hai hằng số cho `GET /v1/meta` (mục 6.1):

| Hằng số | Giá trị |
| --- | --- |
| `ALGORITHM` | `rule_based_weighted` |
| `ALGORITHM_VERSION` | `1.1.1` |

Tăng `ALGORITHM_VERSION` mỗi khi **cách tính điểm hoặc cách dựng lời giải thích** thay đổi, kể cả khi chỉ
đổi một mốc đạt trần hay sửa câu chữ của `text`. Đổi trọng số mặc định cũng là đổi cách tính điểm. Thêm
trọng số mới vào `DEFAULT_WEIGHTS` còn là thay đổi hợp đồng, phải sửa mục 4.4 và mục 6.6 cùng lúc.

| Phiên bản | Thay đổi |
| --- | --- |
| 1.0.0 | Sáu tiêu chí và bảng trọng số mặc định của mục 2 |
| 1.0.1 | Khối tự chọn phải còn hoàn thành đúng được sau mỗi môn được chọn (mục 5); số thập phân trong `text` làm tròn nửa lên, 5,25 thành 5,3; phản hồi có `not_eligible` kèm `text` cho mọi học phần không gợi ý được |
| 1.1.0 | Chọn trong khoảng tín chỉ cho bảng điểm tự nhập (mục 5.4): `not_selected` kèm lý do, cảnh báo, `skip` và `include`; lý do `outstanding_retake` ghi kỳ thứ mấy khi dòng sinh viên không có mã học kỳ. Chọn theo `k` không đổi, nên precision@5 giữ 0,8900 |
| 1.1.1 | Mức sàn của khoảng tín chỉ hạ xuống số tín chỉ còn thiếu để tốt nghiệp khi số đó nhỏ hơn `min_credits`; `credit_window` có `credits_to_graduate`; câu `below_min_credits` nói đúng nguyên nhân (`cause`). Chọn theo `k` không đổi |
