"""Hàm tiện ích chuyển đổi giá trị Python thành dạng JSON-serializable.

Quy tắc:
- NaN / inf → None
- numpy.int64, numpy.float64, numpy.bool_ → int/float/bool Python thuần
- decimal.Decimal → float
- list, dict → đệ quy
- Các kiểu khác giữ nguyên
"""
import math
from decimal import Decimal
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Chuyển `value` thành kiểu Python thuần có thể json.dumps được.

    Dùng chung cho mọi response để tránh lỗi NaN, numpy, Decimal.
    """
    # None giữ nguyên
    if value is None:
        return None

    # float: bắt NaN và infinity → None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    # int Python thuần
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    # bool Python thuần
    if isinstance(value, bool):
        return value

    # Decimal → float
    if isinstance(value, Decimal):
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f

    # Xử lý kiểu numpy nếu có (không import numpy ở đây để tránh phụ thuộc bắt buộc)
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
        # numpy.nan (scalar) – trường hợp hiếm
        try:
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        except (TypeError, ValueError):
            pass

    # Đệ quy cho list / tuple
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]

    # Đệ quy cho dict
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}

    return value


def drop_inapplicable_nulls(obj: Any) -> Any:
    """Lọc bỏ các trường None/null không được phép xuất hiện trong JSON theo mục 3.2.

    Các trường được phép null: gpa, parent_block_code, effective_to_cohort, score/letter_grade môn miễn.
    """
    allowed_null_fields = {"gpa", "parent_block_code", "effective_to_cohort", "score", "letter_grade"}

    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if v is None and k not in allowed_null_fields:
                continue
            cleaned[k] = drop_inapplicable_nulls(v)
        return cleaned
    if isinstance(obj, list):
        return [drop_inapplicable_nulls(item) for item in obj]
    return obj

