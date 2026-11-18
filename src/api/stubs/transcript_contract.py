"""Hằng phản hồi mẫu nguyên văn từ hợp đồng §6.10.

CHỈ dùng làm Stub Fallback khi RULES-4 / DATA-4 chưa merge.
TODO: XÓA khi RULES-4 / DATA-4 merge.
"""
from __future__ import annotations

from typing import Any

# Phản hồi mẫu nguyên văn từ hợp đồng §6.10, chỉ dùng làm Stub Fallback khi RULES-4/DATA-4 chưa merge.
_CONTRACT_TRANSCRIPT_STUB: dict[str, Any] = {
    "credits_earned": 34,
    "credits_outstanding": 3,
    "gpa": 2.76,
    "outstanding_courses": ["MAT2505"],
    "blocks": [
        {"block_code": "I.1", "required_credits": 16, "earned_credits": 8, "counts_toward_total": True},
        {"block_code": "I.2", "required_credits": 5, "earned_credits": 5, "counts_toward_total": True},
        {"block_code": "II", "required_credits": 5, "earned_credits": 2, "counts_toward_total": True},
        {"block_code": "IV", "required_credits": 28, "earned_credits": 13, "counts_toward_total": True},
        {"block_code": "V.1", "required_credits": 49, "earned_credits": 6, "counts_toward_total": True},
    ],
    "summary": {"passed": 10, "retake": 1, "eligible": 15, "missing_prerequisite": 33, "block_complete": 6},
    "courses": [
        {
            "course_code": "MAT2505",
            "course_name": "Lập trình cơ bản",
            "credits": 3,
            "block_code": "III",
            "status": "retake",
            "last_attempt": {"semester": 2, "score": 3.0, "letter_grade": "F"},
            "text": "Cần học lại Lập trình cơ bản: bạn chưa đạt môn này ở kỳ 2 (điểm 3,0).",
        },
        {
            "course_code": "PHI1006",
            "course_name": "Triết học Mác - Lênin",
            "credits": 3,
            "block_code": "I.1",
            "status": "passed",
            "last_attempt": {"semester": 1, "score": 7.5, "letter_grade": "B"},
            "text": "Đã đạt Triết học Mác - Lênin (điểm 7,5).",
        },
    ],
    "warnings": [],
}
