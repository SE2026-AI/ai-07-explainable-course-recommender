"""Lược đồ PostgreSQL: biên dịch được, ràng buộc hoạt động đúng."""
import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from src.data.db.schema import metadata


def test_ddl_bien_dich_duoc():
    for t in metadata.sorted_tables:
        assert "CREATE TABLE" in str(CreateTable(t).compile(dialect=postgresql.dialect()))


def test_truong_khong_co_quan_he_cha_con():
    assert "parent_id" not in metadata.tables["universities"].c


def test_moi_bang_co_khoa_chinh():
    assert all(t.primary_key.columns for t in metadata.tables.values())


def test_moi_truong_co_lich_hoc_ky_rieng_gom_hoc_ky_dang_goi_y(repo_all):
    truong = repo_all._q("SELECT code FROM universities")["code"]
    for u in truong:
        assert repo_all.target_term(u)["term_code"] == repo_all.setting("target_term_code")


def test_song_nganh_duoc_phep_nhung_chi_mot_chuong_trinh_chinh(repo_all):
    them = ("INSERT INTO student_programs (student_id, curriculum_id, cohort_year, status, is_primary) "
            "SELECT sp.student_id, c.id, sp.cohort_year, 'active', {p} FROM student_programs sp "
            "JOIN curricula c ON c.id <> sp.curriculum_id "
            "JOIN majors m ON m.id = c.major_id JOIN students s ON s.id = sp.student_id "
            "WHERE m.university_id = s.university_id ORDER BY sp.id LIMIT 1")
    with repo_all.engine.connect() as c:
        tx = c.begin()
        assert c.execute(text(them.format(p="FALSE"))).rowcount == 1      # ngành thứ hai: được
        tx.rollback()
    with pytest.raises(IntegrityError), repo_all.engine.begin() as c:
        c.execute(text(them.format(p="TRUE")))                              # chương trình chính thứ hai: chặn


def test_log_goi_y_luu_json(repo_all):
    with repo_all.engine.connect() as c:
        tx = c.begin()
        run_id = c.execute(text(
            "INSERT INTO recommendation_runs (student_id, student_program_id, term_id, algorithm, algorithm_version, "
            "parameters) SELECT sp.student_id, sp.id, sp.admission_term_id, 'rule_based', '0.1', "
            "CAST(:p AS JSONB) FROM student_programs sp ORDER BY sp.id LIMIT 1 RETURNING id"),
            {"p": '{"weights": {"grades": 0.7, "interest": 0.3}}'}).scalar()
        w = c.execute(text("SELECT parameters -> 'weights' ->> 'grades' FROM recommendation_runs WHERE id = :i"),
                      {"i": run_id}).scalar()
        assert w == "0.7"
        assert c.execute(text("SELECT created_at FROM recommendation_runs WHERE id = :i"),
                         {"i": run_id}).scalar().tzinfo is not None                  # TIMESTAMPTZ
        tx.rollback()


def test_hai_truong_dung_chung_ma_sinh_vien_va_ma_hoc_phan(repo_all):
    sv = repo_all._q("SELECT u.code, s.student_code FROM students s JOIN universities u ON u.id = s.university_id "
                     "WHERE s.student_code = 'T01'")
    assert set(sv["code"]) == {"HUS", "DEMO"}
    hp = repo_all._q("SELECT u.code FROM courses c JOIN universities u ON u.id = c.university_id WHERE c.code = 'MAT2505'")
    assert set(hp["code"]) == {"HUS", "DEMO"}


@pytest.mark.parametrize("sql", [
    ("INSERT INTO students (university_id, student_code, full_name, is_synthetic) "
    "SELECT university_id, student_code, 'trùng', TRUE FROM students LIMIT 1"),                     # trùng mã trong 1 trường
    ("INSERT INTO course_results (student_id, course_id, term_id, attempt_no, status) "
    "SELECT student_id, course_id, term_id, 9, 'passed' FROM course_results WHERE score IS NOT NULL LIMIT 1"),  # thiếu điểm
    "UPDATE course_results SET status = 'abc' WHERE id = (SELECT MIN(id) FROM course_results)",   # trạng thái sai
    "UPDATE curricula SET status = 'xyz'",                                                       # trạng thái CTĐT sai
    ("INSERT INTO course_results (student_id, course_id, term_id, attempt_no, score, status) "
    "VALUES (999999, 1, 1, 1, 5, 'passed')"),                                                     # khóa ngoại sai
])
def test_rang_buoc_chan_du_lieu_sai(repo_all, sql):
    with pytest.raises(IntegrityError), repo_all.engine.begin() as c:
        c.execute(text(sql))
