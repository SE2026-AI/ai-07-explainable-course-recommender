"""Hàm tiện ích chuyển đổi giá trị Python thành dạng JSON-serializable.

Quy tắc:
- NaN / inf → None
- numpy.int64, numpy.float64, numpy.bool_ → int/float/bool Python thuần
- decimal.Decimal → float
- list, dict → đệ quy
- Các kiểu khác giữ nguyên
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse


def to_jsonable(value: Any) -> Any:
    """Chuyển `value` thành kiểu Python thuần có thể json.dumps được.

    Dùng chung cho mọi response để tránh lỗi NaN, numpy, Decimal.
    """
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return value

    if isinstance(value, bool):
        return value

    if isinstance(value, Decimal):
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f

    type_name = type(value).__name__
    module = getattr(type(value), "__module__", "") or ""
    if module.startswith("numpy"):
        if type_name in ("float16", "float32", "float64", "float128"):
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        if type_name in ("int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"):
            return int(value)
        if type_name in ("bool_",):
            return bool(value)
        try:
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        except (TypeError, ValueError):
            pass

    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]

    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}

    return value


def drop_inapplicable_nulls(obj: Any, is_free_dict: bool = False, in_last_attempt: bool = False) -> Any:
    """Lọc bỏ các trường None/null không được phép xuất hiện trong JSON theo mục 3.2.

    Quy tắc:
    - Không xóa null nằm trong các dict tự do (như 'data' trong reasons hoặc violations).
    - Các trường được phép null ở schema:
      * gpa (sinh viên chưa có điểm)
      * parent_block_code (khối gốc)
      * effective_to_cohort (khung còn hiệu lực)
      * score, letter_grade chỉ khi nằm trong last_attempt (môn miễn)
    """
    if is_free_dict:
        if isinstance(obj, dict):
            return {k: drop_inapplicable_nulls(v, is_free_dict=True) for k, v in obj.items()}
        if isinstance(obj, list):
            return [drop_inapplicable_nulls(item, is_free_dict=True) for item in obj]
        return obj

    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if v is None:
                if k in ("gpa", "parent_block_code", "effective_to_cohort"):
                    cleaned[k] = None
                elif in_last_attempt and k in ("score", "letter_grade"):
                    cleaned[k] = None
                else:
                    # Bỏ các inapplicable null khác
                    continue
            else:
                next_in_last_attempt = (k == "last_attempt")
                next_is_free = (k == "data")
                cleaned[k] = drop_inapplicable_nulls(
                    v,
                    is_free_dict=next_is_free,
                    in_last_attempt=next_in_last_attempt,
                )
        return cleaned

    if isinstance(obj, list):
        return [
            drop_inapplicable_nulls(item, is_free_dict=False, in_last_attempt=in_last_attempt)
            for item in obj
        ]

    return obj


class CleanJSONResponse(JSONResponse):
    """JSONResponse tự động chuẩn hóa và loại bỏ các null không hợp lệ theo hợp đồng."""

    def render(self, content: Any) -> bytes:
        cleaned = drop_inapplicable_nulls(to_jsonable(content))
        return super().render(cleaned)
