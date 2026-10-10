"""View SQL dùng sẵn cho truy vấn hằng ngày (PostgreSQL)."""

VIEWS = {
    # Học phần trong khung, kèm khối và quy tắc chọn – view chính cho thuật toán
    "v_curriculum_courses": """
        SELECT cu.id AS curriculum_id, cu.code AS curriculum_code, u.code AS university_code,
               c.id AS course_id, c.code AS course_code, c.name AS course_name, c.name_en AS course_name_en,
               c.credits, c.teaching_language,
               b.id AS block_id, b.code AS block_code, b.name AS block_name, b.selection_rule,
               CASE WHEN b.selection_rule = 'all' THEN 1 ELSE 0 END AS is_required,
               b.required_credits AS block_required_credits,
               CASE WHEN b.counts_toward_total THEN 1 ELSE 0 END AS counts_toward_total,
               cc.recommended_semester, (cc.recommended_semester + 1) / 2 AS recommended_year, cc.sort_no
        FROM curriculum_courses cc
        JOIN curricula cu ON cu.id = cc.curriculum_id
        JOIN majors m ON m.id = cu.major_id
        JOIN universities u ON u.id = m.university_id
        JOIN courses c ON c.id = cc.course_id
        JOIN curriculum_blocks b ON b.id = cc.block_id
    """,
    # Điều kiện tiên quyết đã đối chiếu: môn yêu cầu có thuộc CTĐT hay không
    "v_prerequisites": """
        SELECT cc.curriculum_id, c.code AS course_code, p.group_no, p.required_course_code, p.requirement_type,
               p.min_score,
               CASE WHEN EXISTS (SELECT 1 FROM curriculum_courses x
                                 WHERE x.curriculum_id = cc.curriculum_id AND x.course_id = p.required_course_id)
                    THEN 1 ELSE 0 END AS in_curriculum
        FROM prerequisites p
        JOIN curriculum_courses cc ON cc.id = p.curriculum_course_id
        JOIN courses c ON c.id = cc.course_id
    """,
    # Sinh viên và CTĐT đang theo học
    "v_student_programs": """
        SELECT s.id AS student_id, u.code AS university_code, s.student_code, s.full_name, s.is_synthetic,
               sp.id AS student_program_id, cu.id AS curriculum_id, cu.code AS curriculum_code,
               m.code AS major_code, m.name AS major_name, sp.cohort_year, sp.status, sp.is_primary
        FROM students s
        JOIN universities u ON u.id = s.university_id
        JOIN student_programs sp ON sp.student_id = s.id
        JOIN curricula cu ON cu.id = sp.curriculum_id
        JOIN majors m ON m.id = cu.major_id
    """,
    # Kết quả học tập kèm mã học kỳ, đánh số lần học mới nhất = 1
    "v_course_results": """
        SELECT r.id AS result_id, r.student_id, c.code AS course_code, r.course_id, t.code AS term_code,
               r.attempt_no, r.score, r.letter_grade, r.grade_point, r.status,
               ROW_NUMBER() OVER (PARTITION BY r.student_id, r.course_id
                                  ORDER BY t.code DESC, r.attempt_no DESC) AS recency
        FROM course_results r
        JOIN courses c ON c.id = r.course_id
        JOIN terms t ON t.id = r.term_id
    """,
    # Tiến độ học tập theo CTĐT chính: tín chỉ tích lũy và điểm trung bình tích lũy (thang 4).
    # Lấy lần học gần nhất của mỗi môn; chỉ tính môn thuộc khối có counts_toward_total.
    "v_student_progress": """
        SELECT sp.student_id, sp.id AS student_program_id,
               COALESCE(SUM(c.credits) FILTER (WHERE r.status IN ('passed', 'exempted') AND b.counts_toward_total), 0)
                   AS credits_earned,
               COALESCE(SUM(c.credits) FILTER (WHERE r.status = 'failed' AND b.counts_toward_total), 0)
                   AS credits_outstanding,
               ROUND(SUM(r.grade_point * c.credits) FILTER (WHERE r.status IN ('passed', 'failed') AND b.counts_toward_total)
                     / NULLIF(SUM(c.credits) FILTER (WHERE r.status IN ('passed', 'failed') AND b.counts_toward_total), 0), 2)
                   AS gpa,
               COUNT(DISTINCT r.term_code) AS terms_studied
        FROM student_programs sp
        LEFT JOIN v_course_results r ON r.student_id = sp.student_id AND r.recency = 1
        LEFT JOIN courses c ON c.id = r.course_id
        LEFT JOIN curriculum_courses cc ON cc.curriculum_id = sp.curriculum_id AND cc.course_id = r.course_id
        LEFT JOIN curriculum_blocks b ON b.id = cc.block_id
        WHERE sp.is_primary
        GROUP BY sp.student_id, sp.id
    """,
}
