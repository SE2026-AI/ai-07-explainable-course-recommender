"""Tầng truy cập dữ liệu trả đúng số liệu mà tầng API và tầng nghiệp vụ sẽ dùng.

Các bài ở đây kiểm chính lớp `Repository`, không kiểm luật học vụ: mỗi hàm phải trả đủ cột mà
hợp đồng API cần, và các số phải khớp với CSV gốc hoặc khớp lẫn nhau.
"""
import pandas as pd
import pytest
from conftest import curricula_codes

CURRICULA = curricula_codes()
SEED = "data/seed/"


def test_universities_match_csv(repo):
    universities = repo.universities()
    csv = pd.read_csv(SEED + "universities.csv")
    assert set(universities.columns) >= {"university_code", "name", "name_en", "short_name", "is_demo"}
    assert list(universities["university_code"]) == sorted(csv["code"])
    assert (universities["is_demo"] == 0).all(), "dữ liệu thật không được chứa trường giả lập"


def test_terms_include_target_term(repo):
    terms = repo.terms("HUS")
    csv = pd.read_csv(SEED + "terms.csv", dtype=str)
    assert list(terms["term_code"]) == sorted(csv["code"]), "thiếu học kỳ, hoặc chưa sắp theo mã"
    assert repo.setting("target_term_code") in set(terms["term_code"])
    assert terms["term_no"].isin([1, 2, 3]).all()
    assert repo.terms("KHONG-CO-TRUONG-NAY").empty


@pytest.mark.parametrize("curriculum", CURRICULA)
def test_blocks_form_a_tree(repo_all, curriculum):
    blocks = repo_all.blocks(curriculum)
    codes = set(blocks["block_code"])
    parents = blocks["parent_block_code"].dropna()
    assert not blocks.empty
    assert set(parents) <= codes, f"{curriculum}: khối cha không tồn tại {set(parents) - codes}"
    assert len(blocks) - len(parents) >= 1, f"{curriculum}: không có khối gốc"
    assert blocks["selection_rule"].isin(["all", "choose_credits", "container"]).all()
    assert (blocks["block_code"].value_counts() == 1).all(), f"{curriculum}: mã khối bị trùng"


@pytest.mark.parametrize("curriculum", CURRICULA)
def test_blocks_cover_elective_blocks(repo_all, curriculum):
    """`blocks` là bản đầy đủ, nên phải phủ được `elective_blocks` và khớp số tín chỉ cần chọn."""
    blocks, electives = repo_all.blocks(curriculum), repo_all.elective_blocks(curriculum)
    assert set(electives["block_code"]) == set(blocks[blocks["selection_rule"] == "choose_credits"]["block_code"])
    required = blocks.set_index("block_code")["required_credits"]
    for _, block in electives.iterrows():
        assert required[block["block_code"]] == block["required_credits"], \
            f"{curriculum} khối {block['block_code']}"


def test_data_issues_match_csv(repo):
    issues = repo.data_issues()
    csv = pd.read_csv(SEED + "data_issues.csv")
    assert len(issues) == len(csv)
    assert set(issues.columns) >= {"source_code", "source_title", "document_number", "entity_type",
                                   "entity_key", "issue_type", "description", "status"}
    assert issues["status"].isin(["open", "resolved_in_data", "closed"]).all()
    assert issues["source_title"].notna().all(), "mỗi vấn đề phải truy được về một văn bản"


def test_block_progress_sums_to_credits_earned(repo):
    """Tín chỉ đã đạt của các khối tính vào tổng phải cộng lại bằng credits_earned của sinh viên."""
    students = repo.students().sort_values("student_code").head(10)
    assert not students.empty
    for _, student in students.iterrows():
        progress = repo.block_progress(student["student_id"])
        counted = progress[progress["counts_toward_total"] == 1]["earned_credits"].sum()
        assert counted == student["credits_earned"], f"sinh viên {student['student_code']}"
        assert (progress[progress["selection_rule"] == "container"]["earned_credits"] == 0).all()
        assert len(progress) == len(repo.blocks(student["curriculum_code"])), "thiếu khối chưa học môn nào"


def _same(a, b):
    """So hai giá trị của một ô, coi NaN bằng NaN."""
    if isinstance(a, float) and isinstance(b, float) and pd.isna(a) and pd.isna(b):
        return True
    return a == b


def test_student_matches_its_row_in_students_for_every_student(repo_all):
    """`student()` lọc kết quả theo học kỳ bằng SQL riêng, vì view `v_student_progress` không nhận tham số.
    Ở học kỳ cần gợi ý, hai đường phải cho cùng giá trị ở MỌI cột — đây là chốt chặn hai bản công thức
    tín chỉ và GPA lệch nhau."""
    students = repo_all.students()
    assert not students.empty
    for _, expected in students.iterrows():
        actual = repo_all.student(expected["university_code"], expected["student_code"])
        assert list(actual.index) == list(expected.index)
        diff = [col for col in expected.index if not _same(actual[col], expected[col])]
        assert not diff, f"{expected['university_code']}/{expected['student_code']}: lệch ở {diff}"


def test_student_sees_only_results_from_terms_before_the_requested_one(repo_all):
    """Hợp đồng mục 3.1: T04 trượt MAT2505 ở kỳ 20242, học lại đạt ở kỳ 20251. Nhìn từ đầu kỳ 20251 thì
    môn đó vẫn đang nợ, và T04 mới học năm thứ hai."""
    before = repo_all.student("HUS", "T04", "20251")
    assert "MAT2505" in before["outstanding_courses"] and "MAT2505" not in before["passed_courses"]
    assert before["latest_attempts"]["MAT2505"] == {"term_code": "20242", "attempt_no": 1, "score": 3.5,
                                                     "letter_grade": "F", "status": "failed"}
    assert before["year_of_study"] == 2
    now = repo_all.student("HUS", "T04")
    assert "MAT2505" in now["passed_courses"] and "MAT2505" not in now["outstanding_courses"]
    assert now["latest_attempts"]["MAT2505"]["term_code"] == "20251"
    assert now["year_of_study"] == 3
    assert before["credits_earned"] < now["credits_earned"]


def test_block_progress_uses_the_same_term_as_student(repo_all):
    for term in ("20251", None):
        student = repo_all.student("HUS", "T04", term)
        progress = repo_all.block_progress(student["student_id"], term)
        assert progress[progress["counts_toward_total"] == 1]["earned_credits"].sum() == student["credits_earned"]


def test_student_is_none_when_unknown_and_rejects_a_term_outside_the_calendar(repo_all):
    assert repo_all.student("HUS", "KHONG-CO") is None
    assert repo_all.student("DEMO", "26000001") is None, "mã sinh viên chỉ duy nhất trong một trường"
    with pytest.raises(KeyError):
        repo_all.student("HUS", "T04", "19991")


def test_student_programs_tell_a_missing_student_from_a_known_one(repo_all):
    assert repo_all.student_programs("HUS", "KHONG-CO").empty
    programs = repo_all.student_programs("HUS", "T04")
    assert len(programs) == 1 and bool(programs.iloc[0]["is_primary"]) and programs.iloc[0]["status"] == "active"


def test_term_looks_up_the_calendar_of_that_university_only(repo_all):
    assert repo_all.term("HUS", "20251")["term_no"] == 1
    with pytest.raises(KeyError):
        repo_all.term("KHONG-CO-TRUONG-NAY", "20251")
