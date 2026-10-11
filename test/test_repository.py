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
