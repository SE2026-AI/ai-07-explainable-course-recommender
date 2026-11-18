"""Hằng phản hồi mẫu nguyên văn từ hợp đồng §6.10 và §6.11.

CHỈ dùng làm Stub Fallback khi RULES-4 / RANK-3 / RULES-6 chưa merge.
TODO: XÓA khi RULES-4 / RANK-3 / RULES-6 merge.
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

# Phản hồi mẫu nguyên văn từ hợp đồng §6.11, chỉ dùng làm Stub Fallback khi RULES-4/DATA-4/RANK-3 chưa merge.
_CONTRACT_RECOMMENDATIONS_STUB: dict[str, Any] = {
    "credit_window_total": 20,
    "credit_window_text": "Tổng 20 tín chỉ, trong khoảng 15–20 bạn đặt.",
    "candidate_count": 16,
    "items": [
        {
            "rank": 1,
            "course_code": "MAT2505",
            "course_name": "Lập trình cơ bản",
            "credits": 3,
            "block_code": "III",
            "status": "retake",
            "score": 5.7083,
            "reasons": [
                {
                    "code": "outstanding_retake",
                    "contribution": 3.0,
                    "text": "Bạn chưa đạt môn này ở kỳ 2 (điểm 3,0).",
                    "data": {"semester": 2, "score": 3.0},
                },
                {
                    "code": "unlocks",
                    "contribution": 1.5,
                    "text": "Đạt môn này sẽ mở khóa 12 học phần khác của chương trình.",
                    "data": {
                        "count": 12,
                        "course_codes": [
                            "MAT1202",
                            "MAT3373E",
                            "MAT3505",
                            "MAT3506",
                            "MAT3507",
                            "MAT3514",
                            "MAT3519",
                            "MAT3539",
                            "MAT3550E",
                            "MAT3554E",
                            "MAT3558",
                            "MAT3560",
                        ],
                    },
                },
                {
                    "code": "overdue",
                    "contribution": 1.0,
                    "text": "Môn này dự kiến học ở kỳ 2, bạn đang ở kỳ 3.",
                    "data": {"recommended_semester": 2, "target_semester": 3, "semesters_late": 1},
                },
                {
                    "code": "strong_topic",
                    "contribution": 0.2083,
                    "text": "Bạn đang học tốt chủ đề Lập trình: điểm trung bình 5,3 trên 2 môn đã học.",
                    "data": {
                        "topic_code": "lap_trinh",
                        "topic_name": "Lập trình",
                        "average_score": 5.25,
                        "course_codes": ["HUS1011", "MAT2505"],
                    },
                },
            ],
        },
        {
            "rank": 7,
            "course_code": "MAT2407",
            "course_name": "Tối ưu hóa",
            "credits": 3,
            "block_code": "IV",
            "status": "eligible",
            "score": 0.5833,
            "reasons": [
                {
                    "code": "strong_topic",
                    "contribution": 0.5833,
                    "text": "Bạn đang học tốt chủ đề Toán: điểm trung bình 7,5 trên 4 môn đã học.",
                    "data": {
                        "topic_code": "toan",
                        "topic_name": "Toán",
                        "average_score": 7.5,
                        "course_codes": ["MAT2400", "MAT2501", "MAT2502", "MAT3500"],
                    },
                }
            ],
        },
    ],
    "not_selected": [
        {
            "course_code": "HUS1024",
            "course_name": "Nhập môn Robotic",
            "credits": 3,
            "block_code": "II",
            "status": "eligible",
            "score": 2.5833,
            "reason": "block_full",
            "text": (
                "Chưa xếp Nhập môn Robotic: khối kiến thức theo lĩnh vực chỉ cần 5 tín chỉ "
                "và đã có 5 từ môn đã đạt và môn xếp trên."
            ),
            "data": {
                "block_code": "II",
                "block_name": "Khối kiến thức theo lĩnh vực",
                "required_credits": 5,
                "taken_credits": 5,
                "credits": 3,
            },
        },
        {
            "course_code": "MAT2503",
            "course_name": "Giải tích 3",
            "credits": 2,
            "block_code": "IV",
            "status": "eligible",
            "score": 2.5833,
            "reason": "skipped",
            "text": "Bạn chọn chưa học Giải tích 3 ở kỳ này.",
            "data": {},
        },
        {
            "course_code": "MAT2403",
            "course_name": "Phương trình vi phân",
            "credits": 3,
            "block_code": "IV",
            "status": "eligible",
            "score": 0.7333,
            "reason": "credit_budget",
            "text": (
                "Chưa xếp Phương trình vi phân: kỳ này đã có 20 tín chỉ, "
                "thêm 3 tín chỉ sẽ vượt mức tối đa 20 bạn đặt."
            ),
            "data": {"credits": 3, "total_credits": 20, "max_credits": 20},
        },
    ],
    "not_eligible": [
        {
            "course_code": "MAT3533",
            "course_name": "Học máy",
            "credits": 3,
            "block_code": "V.1",
            "status": "missing_prerequisite",
            "missing_prerequisites": [["MAT2323"]],
            "text": "Chưa học được Học máy: cần hoàn thành Xác suất - Thống kê (MAT2323) trước.",
        }
    ],
    "warnings": [],
}
