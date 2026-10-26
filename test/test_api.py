"""Kiểm thử tự động 14 endpoint API v1 theo hợp đồng api-contract.md."""
from __future__ import annotations

import ast
import copy
import importlib
import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.deps import get_repo
from src.data.repository import Repository
from src.recommender import ALGORITHM_VERSION

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _has(module_name: str, attr: str) -> bool:
    """True khi module import được và có `attr`. Dùng cho skipif lúc collect: getattr(src, "explain")
    luôn là None vì submodule chưa được import, khiến test bị skip vĩnh viễn."""
    try:
        return hasattr(importlib.import_module(module_name), attr)
    except Exception:
        return False


@pytest.fixture(scope="session")
def api_client(repo):
    """TestClient dùng dữ liệu repo thật (chỉ HUS)."""
    app = create_app()
    app.dependency_overrides[get_repo] = lambda: repo
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def api_client_all(repo_all):
    """TestClient dùng repo_all (HUS + DEMO)."""
    app = create_app()
    app.dependency_overrides[get_repo] = lambda: repo_all
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def api_client_no_db():
    """TestClient KHÔNG cần DB – dùng mock repo. Dành cho test 404 route, 503, v.v."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# =====================================================================
# 1. GET /v1/health
# =====================================================================

def test_health(api_client: TestClient, repo, monkeypatch: pytest.MonkeyPatch):
    """GET /v1/health trả 200, không bọc meta.

    /health không đi qua Depends(get_repo) nên phải thay `_create_repo` bằng repo kiểm thử; nếu không,
    test sẽ nối vào database thật ở DATABASE_URL (có thể chưa nạp dữ liệu, như trên CI).
    """
    monkeypatch.setattr("src.api.routers.system._create_repo", lambda: repo)
    r = api_client.get("/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "up"
    assert "meta" not in data


# =====================================================================
# 2. GET /v1/meta
# =====================================================================

def test_meta(api_client: TestClient):
    """GET /v1/meta (mục 6.1) trả đủ các trường cấu hình."""
    r = api_client.get("/v1/meta")
    assert r.status_code == 200
    data = r.json()
    assert data["api_version"] == "1.0.0"
    assert data["schema_version"] == "3.0.0"
    assert data["algorithm"] == "rule_based_weighted"
    assert data["algorithm_version"] == ALGORITHM_VERSION
    assert data["default_term"] == "20261"
    assert "HUS-7480113QTD-2022" in data["curriculum_codes"]


# =====================================================================
# 3. GET /v1/universities
# =====================================================================

def test_universities(api_client: TestClient):
    """GET /v1/universities trả danh sách trường."""
    r = api_client.get("/v1/universities")
    assert r.status_code == 200
    unis = r.json()
    assert isinstance(unis, list)
    codes = [u["university_code"] for u in unis]
    assert "HUS" in codes


# =====================================================================
# 4. GET /v1/universities/{uni}/terms
# =====================================================================

def test_terms_success(api_client: TestClient):
    """GET /v1/universities/HUS/terms trả danh sách kỳ sắp theo code tăng dần."""
    r = api_client.get("/v1/universities/HUS/terms")
    assert r.status_code == 200
    terms = r.json()
    assert len(terms) > 0
    codes = [t["term_code"] for t in terms]
    assert codes == sorted(codes)
    assert any(t["term_code"] == "20261" for t in terms)


def test_terms_university_not_found(api_client: TestClient):
    """Trường không tồn tại -> 404 university_not_found."""
    r = api_client.get("/v1/universities/UNKNOWN_UNI/terms")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "university_not_found"
    assert isinstance(err["details"], dict)
    assert "request_id" not in err


# =====================================================================
# 5. GET /v1/universities/{uni}/curricula
# =====================================================================

def test_curricula_of_university(api_client: TestClient):
    """GET /v1/universities/HUS/curricula trả danh sách khung của trường."""
    r = api_client.get("/v1/universities/HUS/curricula")
    assert r.status_code == 200
    curricula = r.json()
    assert len(curricula) >= 2
    for c in curricula:
        assert c["university_code"] == "HUS"


# =====================================================================
# 6. GET /v1/universities/{uni}/curricula/{curriculum_code}
# =====================================================================

def test_curriculum_detail(api_client: TestClient):
    """GET /v1/universities/HUS/curricula/HUS-7480113QTD-2022 (mục 6.2)."""
    r = api_client.get("/v1/universities/HUS/curricula/HUS-7480113QTD-2022")
    assert r.status_code == 200
    data = r.json()
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["university_code"] == "HUS"
    assert "blocks" in data
    blocks = data["blocks"]
    assert len(blocks) > 0
    # Khối gốc có parent_block_code là null
    root_blocks = [b for b in blocks if b["parent_block_code"] is None]
    assert len(root_blocks) >= 1


def test_curriculum_not_found_wrong_university(api_client_all: TestClient):
    """Mã khung không thuộc trường trong đường dẫn -> 404 curriculum_not_found (mục 1.3)."""
    r = api_client_all.get("/v1/universities/DEMO/curricula/HUS-7480113QTD-2022")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "curriculum_not_found"


# =====================================================================
# 7. GET /v1/universities/{uni}/curricula/{curriculum_code}/courses
# =====================================================================

def test_curriculum_courses(api_client: TestClient):
    """GET /v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses (mục 6.3)."""
    r = api_client.get("/v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses")
    assert r.status_code == 200
    data = r.json()
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["count"] == len(data["courses"])
    assert data["count"] > 0
    c0 = data["courses"][0]
    assert "course_code" in c0
    assert "prerequisite_groups" in c0
    assert isinstance(c0["prerequisite_groups"], list)


# =====================================================================
# 8. GET /v1/data-issues
# =====================================================================

def test_data_issues(api_client: TestClient):
    """GET /v1/data-issues (mục 6.8)."""
    r = api_client.get("/v1/data-issues")
    assert r.status_code == 200
    data = r.json()
    assert "count" in data
    assert "issues" in data
    assert data["count"] == len(data["issues"])
    assert data["count"] > 0


# =====================================================================
# 9. Bất biến lỗi & Định dạng lỗi chung (mục 5)
# =====================================================================

def test_invariant_error_format(api_client_all: TestClient):
    """Mọi phản hồi từ 400 trở lên khớp lược đồ ở mục 5."""
    r_404 = api_client_all.get("/v1/universities/UNKNOWN_UNI/terms")
    assert r_404.status_code == 404
    body = r_404.json()
    assert "error" in body
    err = body["error"]
    assert "code" in err and isinstance(err["code"], str)
    assert "message" in err and isinstance(err["message"], str)
    assert "details" in err and isinstance(err["details"], dict)
    assert "request_id" not in err

    # 422
    app = create_app()

    @app.get("/v1/test-validation-invariant")
    def dummy_route(param: int):
        return {"param": param}

    client = TestClient(app)
    r_422 = client.get("/v1/test-validation-invariant?param=not-an-int")
    assert r_422.status_code == 422
    err_422 = r_422.json()["error"]
    assert err_422["code"] == "validation_error"
    assert isinstance(err_422["details"], dict)
    assert "request_id" not in err_422


def test_validation_error_format():
    """Kiểm tra định dạng lỗi 422 validation_error theo hợp đồng mục 5."""
    app = create_app()

    @app.get("/v1/test-validation")
    def dummy_route(param: int):
        return {"param": param}

    client = TestClient(app)
    r = client.get("/v1/test-validation?param=not-an-int")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert isinstance(err["details"], dict)
    assert "fields" in err["details"]
    assert "param" in err["details"]["fields"]
    assert "request_id" not in err


def test_route_not_found(api_client_no_db: TestClient):
    """Đường dẫn không tồn tại -> 404 route_not_found."""
    r = api_client_no_db.get("/v1/nonexistent-route-xyz")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "route_not_found"
    assert isinstance(err["details"], dict)
    assert "request_id" not in err


def test_method_not_allowed(api_client_no_db: TestClient):
    """Phương thức HTTP không hỗ trợ -> 405 method_not_allowed."""
    r = api_client_no_db.post("/v1/health")
    assert r.status_code == 405
    err = r.json()["error"]
    assert err["code"] == "method_not_allowed"
    assert isinstance(err["details"], dict)
    assert "request_id" not in err


def test_internal_error_format():
    """Kiểm tra định dạng lỗi 500 internal_error không lộ chi tiết nội bộ."""
    app = create_app()

    @app.get("/v1/test-crash")
    def dummy_crash():
        raise RuntimeError("Secret DB connection string failed!")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/v1/test-crash")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "internal_error"
    assert "Secret DB connection string" not in r.text
    assert "request_id" not in err


def test_openapi_matches_committed_file():
    """docs/api/openapi.json đã commit phải khớp với app.openapi()."""
    committed_path = PROJECT_ROOT / "docs" / "api" / "openapi.json"
    assert committed_path.exists(), "docs/api/openapi.json chưa tồn tại"

    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    current = create_app().openapi()

    def _normalize(spec: dict) -> dict:
        # Chuẩn hóa khác biệt giữa Pydantic 2.9 (không có additionalProperties) và Pydantic 2.10+ (có additionalProperties: True)

        s = copy.deepcopy(spec)

        def _clean(d):
            if isinstance(d, dict):
                if d.get("title") == "Details" and d.get("type") == "object":
                    d.pop("additionalProperties", None)
                for v in d.values():
                    _clean(v)
            elif isinstance(d, list):
                for x in d:
                    _clean(x)

        _clean(s)
        return s

    assert _normalize(committed) == _normalize(current), "docs/api/openapi.json không khớp với app.openapi()"


# =====================================================================
# 10. Gaps & Schema Invariants (mục catalog & system)
# =====================================================================

def test_no_inapplicable_nulls_in_catalog_and_system(api_client_all: TestClient):
    """Lỗi 5: null rò rỉ ở catalog và system.

    Duyệt đệ quy mọi phản hồi catalog & system, chỉ chấp nhận null ở tập khóa được phép:
    parent_block_code, effective_to_cohort.
    """
    client = api_client_all
    allowed_null_keys = {"parent_block_code", "effective_to_cohort"}

    def assert_no_forbidden_null(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                cur_path = f"{path}.{k}" if path else k
                if v is None:
                    assert k in allowed_null_keys, (
                        f"Phát hiện null không hợp lệ tại '{cur_path}' (khóa '{k}' không nằm trong {allowed_null_keys})"
                    )
                else:
                    assert_no_forbidden_null(v, cur_path)
        elif isinstance(obj, list):
            for i, it in enumerate(obj):
                assert_no_forbidden_null(it, f"{path}[{i}]")

    urls = [
        "/v1/meta",
        "/v1/universities",
        "/v1/data-issues",
        "/v1/universities/HUS/terms",
        "/v1/universities/HUS/curricula",
        "/v1/universities/HUS/curricula/HUS-7480113QTD-2022",
        "/v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses",
    ]

    for url in urls:
        resp = client.get(url)
        assert resp.status_code == 200, f"{url} trả về {resp.status_code}: {resp.text}"
        assert_no_forbidden_null(resp.json(), path=url)


def test_no_sql_outside_data_layer():
    """Lỗi 6: SQL trong tầng API (_q / SELECT ngoài src/data/).

    Quét AST mọi file .py dưới src/api/, src/rules/, src/recommender/, src/explain/:
    Khẳng định KHÔNG có lời gọi _q( và KHÔNG có chuỗi 'SELECT ' (bỏ qua docstring/comment).
    """
    dirs_to_check = ["src/api", "src/rules", "src/recommender", "src/explain"]

    violations = []

    for d in dirs_to_check:
        dir_path = PROJECT_ROOT / d
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code, filename=str(py_file))

            docstring_nodes = set()
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    docstring_nodes.add(node.body[0].value)

            for node in ast.walk(tree):
                # 1. Kiểm tra gọi hàm _q(...)
                if isinstance(node, ast.Call):
                    is_q = (
                        (isinstance(node.func, ast.Attribute) and node.func.attr == "_q")
                        or (isinstance(node.func, ast.Name) and node.func.id == "_q")
                    )
                    if is_q:
                        violations.append(
                            f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno}: Gọi hàm nội bộ '_q'"
                        )

                # 2. Kiểm tra chuỗi chứa 'SELECT ' ngoài docstring
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node not in docstring_nodes
                    and "SELECT " in node.value.upper()
                ):
                    violations.append(
                        f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno}: Chứa chuỗi SQL '{node.value.strip()[:40]}...'"
                    )

    assert not violations, "Phát hiện SQL / _q vi phạm kiến trúc data-model:\n" + "\n".join(violations)


def test_openapi_enums_enforced():
    """Lỗi 7: Khóa hợp đồng bằng kiểu dữ liệu (Literal enums + xuất lại OpenAPI).

    Đọc docs/api/openapi.json và khẳng định các trường enum được khai báo chính xác.
    """
    openapi_path = PROJECT_ROOT / "docs" / "api" / "openapi.json"
    assert openapi_path.exists(), "docs/api/openapi.json chưa tồn tại"

    with open(openapi_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    schemas = spec.get("components", {}).get("schemas", {})

    expected_enums = {
        ("CurriculumBlockOut", "selection_rule"): {
            "all",
            "choose_credits",
            "container",
        },
        ("DataIssueItemOut", "status"): {
            "open",
            "resolved_in_data",
            "closed",
        },
        ("CourseStatusItemOut", "status"): {
            "passed",
            "block_complete",
            "missing_prerequisite",
            "retake",
            "eligible",
        },
    }

    errors = []
    for (schema_name, field_name), exp_set in expected_enums.items():
        schema = schemas.get(schema_name)
        if not schema:
            errors.append(f"Schema '{schema_name}' không tồn tại trong openapi.json")
            continue
        field_prop = schema.get("properties", {}).get(field_name, {})
        actual_enum = field_prop.get("enum")
        if actual_enum is None:
            errors.append(f"'{schema_name}.{field_name}' không có trường 'enum' trong OpenAPI spec")
        elif set(actual_enum) != exp_set:
            errors.append(
                f"'{schema_name}.{field_name}' enum không khớp. Nhận được: {set(actual_enum)}, Kỳ vọng: {exp_set}"
            )

    assert not errors, "Các trường enum OpenAPI chưa được khóa đúng hợp đồng:\n" + "\n".join(errors)


# =====================================================================
# 11. Health Database Down & CleanJSONResponse (API-3)
# =====================================================================

def test_health_database_down():
    """GET /v1/health trả 503 theo §5 khi kết nối DB lỗi."""
    from unittest.mock import MagicMock, patch

    mock_repo = MagicMock()
    mock_repo.setting.side_effect = RuntimeError("Mất kết nối database PostgreSQL")

    with patch("src.api.routers.system._create_repo", return_value=mock_repo):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/health")

    assert r.status_code == 503
    body = r.json()
    # Phải tuân thủ §5 envelope
    assert "error" in body
    err = body["error"]
    assert err["code"] == "service_unavailable"
    assert isinstance(err["message"], str) and len(err["message"]) > 0
    assert isinstance(err["details"], dict)
    assert err["details"]["database"] == "down"


def test_health_database_down_create_repo_fails():
    """GET /v1/health trả 503 theo §5 khi _create_repo() raise Exception (DB không kết nối được)."""
    from unittest.mock import patch

    with patch("src.api.routers.system._create_repo", side_effect=RuntimeError("Connection refused")):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/health")

    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "service_unavailable"
    assert err["details"]["database"] == "down"
    # Không lộ thông tin nội bộ
    assert "Connection refused" not in r.text


def test_clean_json_response_null_handling():
    """Kiểm tra CleanJSONResponse và drop_inapplicable_nulls:

    - Không xóa null trong các dict tự do (reasons[].data, violations[].data).
    - Giữ null ở các trường được phép: gpa, parent_block_code, effective_to_cohort,
      last_attempt.score, last_attempt.letter_grade.
    - Lọc bỏ inapplicable null ở các trường khác.
    """
    from src.api.serialization import drop_inapplicable_nulls

    raw_payload = {
        "university_code": "HUS",
        "gpa": None,
        "items": [
            {
                "course_code": "MAT1001",
                "score": 8.0,
                "reasons": [
                    {
                        "code": "unlocks",
                        "contribution": 1.5,
                        "data": {"count": 5, "missing_extra_field": None},
                    }
                ],
            }
        ],
        "courses": [
            {
                "course_code": "MAT2505",
                "last_attempt": {
                    "term_code": "20251",
                    "attempt_no": 1,
                    "score": None,
                    "letter_grade": None,
                },
                "missing_prerequisites": None,
            }
        ],
        "extra_null_field": None,
    }

    cleaned = drop_inapplicable_nulls(raw_payload)

    assert "extra_null_field" not in cleaned
    assert "missing_prerequisites" not in cleaned["courses"][0]
    assert cleaned["gpa"] is None
    assert cleaned["courses"][0]["last_attempt"]["score"] is None
    assert cleaned["courses"][0]["last_attempt"]["letter_grade"] is None
    assert cleaned["items"][0]["reasons"][0]["data"]["missing_extra_field"] is None


# =====================================================================
# 12. Endpoints Sinh Viên: profile & course-status (API-1)
# =====================================================================

def test_student_profile_t03(api_client_all: TestClient):
    """GET .../profile cho sinh viên T03 (mục 6.4) khớp dữ liệu hợp đồng."""
    r = api_client_all.get("/v1/universities/HUS/students/T03/profile?term=20261")
    assert r.status_code == 200
    data = r.json()
    assert data["university_code"] == "HUS"
    assert data["student_code"] == "T03"
    assert data["full_name"] == "Sinh viên test HUS T03"
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["major_code"] == "7480113QTD"
    assert data["major_name"] == "Khoa học máy tính và thông tin"
    assert data["cohort_year"] == 2025
    assert data["year_of_study"] == 2
    assert data["term"] == "20261"
    assert data["target_semester"] == 3
    assert data["credits_earned"] == 34
    assert data["credits_outstanding"] == 3
    assert data["total_credits"] == 129
    assert data["gpa"] == 2.76
    assert data["max_credits_per_term"] == 40
    assert data["interests"] == ["phan_mem"]
    assert data["outstanding_courses"] == ["MAT2505"]

    expected_blocks = [
        {"block_code": "I.1", "required_credits": 16, "earned_credits": 8, "counts_toward_total": True},
        {"block_code": "I.2", "required_credits": 5, "earned_credits": 5, "counts_toward_total": True},
        {"block_code": "II", "required_credits": 5, "earned_credits": 2, "counts_toward_total": True},
        {"block_code": "IV", "required_credits": 28, "earned_credits": 13, "counts_toward_total": True},
        {"block_code": "V.1", "required_credits": 49, "earned_credits": 6, "counts_toward_total": True},
    ]
    assert data["blocks"] == expected_blocks


def test_student_profile_target_semester_by_term(api_client_all: TestClient):
    """Mục 2.1: target_semester và year_of_study của profile thay đổi chính xác theo term."""
    # Kỳ 20251: năm 1, kỳ 1 -> target_semester = 1, year_of_study = 1
    r1 = api_client_all.get("/v1/universities/HUS/students/T03/profile?term=20251")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["term"] == "20251"
    assert d1["year_of_study"] == 1
    assert d1["target_semester"] == 1

    # Kỳ 20252: năm 1, kỳ 2 -> target_semester = 2, year_of_study = 1
    r2 = api_client_all.get("/v1/universities/HUS/students/T03/profile?term=20252")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["term"] == "20252"
    assert d2["year_of_study"] == 1
    assert d2["target_semester"] == 2

    # Kỳ 20261: năm 2, kỳ 1 -> target_semester = 3, year_of_study = 2
    r3 = api_client_all.get("/v1/universities/HUS/students/T03/profile?term=20261")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["term"] == "20261"
    assert d3["year_of_study"] == 2
    assert d3["target_semester"] == 3


def test_student_profile_null_gpa(api_client_all: TestClient):
    """Sinh viên T01 năm 1 chưa có điểm thì gpa là null (mục 3.2 và 6.4)."""
    r = api_client_all.get("/v1/universities/HUS/students/T01/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["student_code"] == "T01"
    assert data["gpa"] is None
    assert ('"gpa":null' in r.text) or ('"gpa": null' in r.text)


def test_student_profile_errors(api_client_all: TestClient):
    """Kiểm tra các mã lỗi 404 cho sinh viên: university_not_found, student_not_found, term_not_found."""
    # 404 university_not_found
    r1 = api_client_all.get("/v1/universities/UNKNOWN/students/T03/profile")
    assert r1.status_code == 404
    assert r1.json()["error"]["code"] == "university_not_found"

    # 404 student_not_found
    r2 = api_client_all.get("/v1/universities/HUS/students/UNKNOWN/profile")
    assert r2.status_code == 404
    assert r2.json()["error"]["code"] == "student_not_found"

    # 404 term_not_found
    r3 = api_client_all.get("/v1/universities/HUS/students/T03/profile?term=99999")
    assert r3.status_code == 404
    assert r3.json()["error"]["code"] == "term_not_found"


def test_student_no_primary_program(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Lỗi 409 no_primary_program khi sinh viên không có CTĐT chính hoạt động."""
    orig_programs = Repository.student_programs

    def mock_programs(self, university_code, student_code):
        df = orig_programs(self, university_code, student_code).copy()
        if student_code == "T03":
            df["is_primary"] = False
        return df

    monkeypatch.setattr(Repository, "student_programs", mock_programs)
    r = api_client_all.get("/v1/universities/HUS/students/T03/profile")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_primary_program"


def test_course_status_summary_matches_expected_for_all_test_students(api_client_all: TestClient):
    """Summary của course-status khớp expected_course_status.csv cho toàn bộ sinh viên kiểm thử."""
    import pandas as pd
    expected_df = pd.read_csv(PROJECT_ROOT / "test" / "fixtures" / "students" / "expected_course_status.csv")
    students_in_test = expected_df[["university_code", "student_code"]].drop_duplicates()

    for _, s_row in students_in_test.iterrows():
        u = str(s_row["university_code"])
        s = str(s_row["student_code"])
        r = api_client_all.get(f"/v1/universities/{u}/students/{s}/course-status")
        assert r.status_code == 200, f"Sinh viên {u}/{s} lỗi: {r.text}"
        data = r.json()
        summary = data["summary"]

        s_expected = expected_df[(expected_df["university_code"] == u) & (expected_df["student_code"] == s)]
        counts = s_expected["expected_status"].value_counts().to_dict()

        for status_key in ("passed", "retake", "eligible", "missing_prerequisite", "block_complete"):
            exp_val = counts.get(status_key, 0)
            act_val = summary.get(status_key, 0)
            assert act_val == exp_val, f"Sinh viên {u}/{s}: trạng thái {status_key} mong đợi {exp_val}, nhận {act_val}"

        total_courses = len(data["courses"])
        assert sum(summary.values()) == total_courses


def test_course_status_example_t03(api_client_all: TestClient):
    """GET .../course-status cho T03 (mục 6.5) trả đúng trạng thái các môn mẫu."""
    r = api_client_all.get("/v1/universities/HUS/students/T03/course-status?term=20261")
    assert r.status_code == 200
    data = r.json()
    assert data["university_code"] == "HUS"
    assert data["student_code"] == "T03"
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["term"] == "20261"
    assert data["summary"] == {"passed": 10, "retake": 1, "eligible": 15, "missing_prerequisite": 33, "block_complete": 6}

    courses_by_code = {c["course_code"]: c for c in data["courses"]}
    assert courses_by_code["MAT2505"]["status"] == "retake"
    assert courses_by_code["MAT2505"]["last_attempt"]["score"] == 3.0
    assert courses_by_code["MAT2505"]["last_attempt"]["letter_grade"] == "F"

    assert courses_by_code["MAT3533"]["status"] == "missing_prerequisite"
    assert courses_by_code["MAT3533"]["missing_prerequisites"] == [["MAT2323"]]

    assert courses_by_code["FLF1207"]["status"] == "block_complete"
    assert courses_by_code["FLF1207"]["block"]["block_code"] == "I.2"

    assert courses_by_code["MAT2323"]["status"] == "eligible"

    assert courses_by_code["PHI1006"]["status"] == "passed"
    assert courses_by_code["PHI1006"]["last_attempt"]["score"] == 7.5


def test_course_status_integration_with_stub(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra ghép nối course-status với stub status_text (chờ EXPLAIN-1)."""
    import src.explain
    monkeypatch.setattr(
        src.explain,
        "status_text",
        lambda course, detail, names: f"Giải thích cho {course['course_code']}",
        raising=False,
    )

    r = api_client_all.get("/v1/universities/HUS/students/T03/course-status?term=20261")
    assert r.status_code == 200
    data = r.json()
    courses_by_code = {c["course_code"]: c for c in data["courses"]}
    assert courses_by_code["MAT2505"]["status"] == "retake"
    assert courses_by_code["MAT2505"]["text"] == "Giải thích cho MAT2505"


# =====================================================================
# 13. Gợi ý học phần & Kế hoạch (API-2)
# =====================================================================

def test_recommendations_limits_and_weights_validation(api_client_all: TestClient):
    """Kiểm tra validation cho limit, weights và assumptions ở recommendations."""
    # limit ngoài khoảng [1, 20]
    r1 = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?limit=0")
    assert r1.status_code == 422
    assert r1.json()["error"]["code"] == "validation_error"

    r2 = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?limit=25")
    assert r2.status_code == 422
    assert r2.json()["error"]["code"] == "validation_error"

    # weights có trọng số âm
    r3 = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"weights": {"overdue": -1.0}},
    )
    assert r3.status_code == 422
    assert r3.json()["error"]["code"] == "validation_error"

    # weights có khóa lạ
    r4 = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"weights": {"unknown_weight": 2.0}},
    )
    assert r4.status_code == 422
    assert r4.json()["error"]["code"] == "validation_error"


def test_plan_check_credits(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """POST .../plan-check tính total_credits (17 tín chỉ) và max_credits_per_term (40 tín chỉ).

    Kiểm tra bất biến §6.7:
    - Bỏ trùng: mã môn lặp lại không cộng dồn tín chỉ nhiều lần.
    - Khối không tích lũy: môn thuộc khối có counts_toward_total = False (ví dụ HUS1012 khối I.3)
      không được cộng vào total_credits.
    """
    import src.explain
    import src.rules.plan
    monkeypatch.setattr(src.rules.plan, "check_plan", lambda *a: [])
    monkeypatch.setattr(src.explain, "violation_text", lambda *a: "")

    body = {
        "term": "20261",
        "course_codes": ["MAT2505", "MAT2323", "MAT2503", "PHI1002", "HIS1056", "MAT3533"],
    }
    r = api_client_all.post("/v1/universities/HUS/students/T03/plan-check", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["total_credits"] == 17
    assert data["max_credits_per_term"] == 40
    assert data["university_code"] == "HUS"
    assert data["student_code"] == "T03"
    assert data["valid"] is True

    # Thêm môn HUS1012 (khối I.3 có counts_toward_total = False, 3 tín chỉ)
    # và lặp lại môn MAT2505 -> total_credits vẫn phải bằng 17
    body_with_extra = {
        "term": "20261",
        "course_codes": [
            "MAT2505", "MAT2323", "MAT2503", "PHI1002", "HIS1056", "MAT3533",
            "HUS1012",  # counts_toward_total = False
            "MAT2505",  # mã môn trùng lặp
        ],
    }
    r2 = api_client_all.post("/v1/universities/HUS/students/T03/plan-check", json=body_with_extra)
    assert r2.status_code == 200
    assert r2.json()["total_credits"] == 17


def test_plan_check_violations_contract(api_client_all: TestClient):
    """Kiểm tra các bất biến của plan-check (§6.7, §7) khi có RULES-2 và EXPLAIN-1."""
    body = {
        "term": "20261",
        "course_codes": ["MAT2505", "MAT2323", "MAT2503", "PHI1002", "HIS1056", "MAT3533"],
    }
    r = api_client_all.post("/v1/universities/HUS/students/T03/plan-check", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["total_credits"] == 17
    assert data["max_credits_per_term"] == 40

    violation_codes = [v["code"] for v in data["violations"]]
    violation_courses = [v.get("course_code") for v in data["violations"]]
    assert "missing_prerequisite" in violation_codes
    assert "MAT3533" in violation_courses

    assert (len(data["violations"]) == 0) == data["valid"]


def test_recommendations_contract_invariants(api_client_all: TestClient):
    """Bất biến §7 cho recommendations."""
    import pandas as pd

    r = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?term=20261&limit=5")
    assert r.status_code == 200
    data = r.json()

    exp_status_df = pd.read_csv(PROJECT_ROOT / "test" / "fixtures" / "students" / "expected_course_status.csv")
    t03_status = exp_status_df[
        (exp_status_df["university_code"] == "HUS") & (exp_status_df["student_code"] == "T03")
    ].set_index("course_code")["expected_status"].to_dict()

    for item in data["items"]:
        c_code = item["course_code"]
        assert c_code in t03_status
        assert t03_status[c_code] in ("eligible", "retake")

    for item in data["items"]:
        contrib_sum = sum(reason["contribution"] for reason in item["reasons"])
        assert item["score"] == round(contrib_sum, 4)

    resp_weights = data["weights"]
    for item in data["items"]:
        for reason in item["reasons"]:
            assert reason["code"] in resp_weights

    r_cs = api_client_all.get("/v1/universities/HUS/students/T03/course-status?term=20261")
    assert r_cs.status_code == 200
    cs_data = r_cs.json()
    cs_not_eligible_codes = [c["course_code"] for c in cs_data["courses"] if c["status"] not in ("eligible", "retake")]
    rec_not_eligible_codes = [c["course_code"] for c in data["not_eligible"]]
    assert rec_not_eligible_codes == cs_not_eligible_codes

    r_repeat = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?term=20261&limit=5")
    assert r.content == r_repeat.content


def test_recommendations_precision_at_5(api_client_all: TestClient):
    """Bất biến Có ích (§7): đo precision@5 so với course_registrations.csv của kỳ 20261, trung bình >= 0.85."""
    import pandas as pd
    # dtype=str: mã sinh viên như 23000001 không được đọc thành số, nếu không so sánh với chuỗi luôn sai.
    regs_df = pd.read_csv(PROJECT_ROOT / "data" / "synthetic" / "course_registrations.csv", dtype=str)
    regs_20261 = regs_df[regs_df["term_code"].astype(str) == "20261"]

    synthetic_students = pd.read_csv(PROJECT_ROOT / "data" / "synthetic" / "students.csv", dtype=str)
    precisions = []

    for _, s in synthetic_students.iterrows():
        u = str(s["university_code"])
        sc = str(s["student_code"])
        actual_registered = set(
            regs_20261[(regs_20261["university_code"] == u) & (regs_20261["student_code"] == sc)]["course_code"]
        )
        if not actual_registered:
            continue

        r = api_client_all.get(f"/v1/universities/{u}/students/{sc}/recommendations?term=20261&limit=5")
        assert r.status_code == 200, f"{u}/{sc}: {r.status_code} {r.text}"
        rec_codes = [it["course_code"] for it in r.json()["items"][:5]]
        hits = sum(1 for c in rec_codes if c in actual_registered)
        # Không gợi ý gì thì precision = 0, không bỏ qua sinh viên đó.
        precisions.append(hits / len(rec_codes) if rec_codes else 0.0)

    assert len(precisions) > 0, "Không có dữ liệu sinh viên nào để tính precision@5"
    mean_p5 = sum(precisions) / len(precisions)
    print(f"precision@5 = {mean_p5:.4f} trên {len(precisions)} sinh viên")  # ghi số này vào mô tả PR
    assert mean_p5 >= 0.85, f"Precision@5 đo được {mean_p5:.4f} < ngưỡng hợp đồng 0.85"


# =====================================================================
# 14. Sơ đồ tiên quyết (prerequisite-graph, mục 6.9)
# =====================================================================

def test_prerequisite_graph_errors(api_client_all: TestClient):
    """Kiểm tra lỗi 404 cho prerequisite-graph."""
    # 404 university_not_found
    r1 = api_client_all.get("/v1/universities/UNKNOWN/curricula/HUS-7480113QTD-2022/prerequisite-graph")
    assert r1.status_code == 404
    assert r1.json()["error"]["code"] == "university_not_found"

    # 404 curriculum_not_found
    r2 = api_client_all.get("/v1/universities/HUS/curricula/UNKNOWN_CURRICULUM/prerequisite-graph")
    assert r2.status_code == 404
    assert r2.json()["error"]["code"] == "curriculum_not_found"


@pytest.mark.skipif(hasattr(Repository, "prerequisite_graph"), reason="DATA-2 đã merge")
def test_prerequisite_graph_waits_for_data2(api_client_all: TestClient):
    """Khi Repository.prerequisite_graph chưa có: 500 internal_error rõ ràng, không tự dựng đồ thị trong API."""
    r = api_client_all.get("/v1/universities/HUS/curricula/HUS-7480113QTD-2022/prerequisite-graph")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


@pytest.mark.skipif(not hasattr(Repository, "prerequisite_graph"), reason="chờ DATA-2")
def test_prerequisite_graph_contract(api_client_all: TestClient):
    """Kiểm tra các bất biến của prerequisite-graph (§6.9) khi DATA-2 đã merge."""
    r = api_client_all.get("/v1/universities/HUS/curricula/HUS-7480113QTD-2022/prerequisite-graph")
    assert r.status_code == 200
    data = r.json()

    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    nodes = data["nodes"]
    edges = data["edges"]

    node_codes = {n["course_code"] for n in nodes}
    all_codes = {c["course_code"] for c in api_client_all.get(
        "/v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses").json()["courses"]}
    assert node_codes == all_codes  # nodes gồm mọi học phần của khung
    keys = [(e["course_code"], e["group_no"], e["required_course_code"]) for e in edges]
    assert keys == sorted(keys)  # §3.3
    for e in edges:
        assert e["course_code"] in node_codes
        assert e["required_course_code"] in node_codes

    r_courses = api_client_all.get("/v1/universities/HUS/curricula/HUS-7480113QTD-2022/courses")
    assert r_courses.status_code == 200
    courses_data = r_courses.json()["courses"]
    courses_map = {c["course_code"]: c["prerequisite_groups"] for c in courses_data}

    edges_grouped: dict[str, dict[int, list[str]]] = {}
    for e in edges:
        c = e["course_code"]
        g = e["group_no"]
        req = e["required_course_code"]
        edges_grouped.setdefault(c, {}).setdefault(g, []).append(req)

    for c_code, groups_dict in edges_grouped.items():
        reconstructed_groups = [sorted(groups_dict[g]) for g in sorted(groups_dict.keys())]
        expected_groups = [sorted(grp) for grp in courses_map[c_code]]
        assert reconstructed_groups == expected_groups


# =====================================================================
# 15. Quét khóa cấm (Bảo mật & công bằng, mục 7)
# =====================================================================

@pytest.mark.parametrize(
    "method,endpoint,body,skip_reason",
    [
        ("GET", "/v1/universities/HUS/students/T03/profile", None, None),
        (
            "GET",
            "/v1/universities/HUS/students/T03/course-status",
            None,
            None,
        ),
        (
            "GET",
            "/v1/universities/HUS/students/T03/recommendations",
            None,
            None,
        ),
        (
            "POST",
            "/v1/universities/HUS/students/T03/recommendations",
            {"term": "20261", "limit": 5, "weights": {"outstanding_retake": 3.0}},
            None,
        ),
        (
            "POST",
            "/v1/universities/HUS/students/T03/plan-check",
            {"term": "20261", "course_codes": ["MAT2505", "MAT2323"]},
            None,
        ),
    ],
)
def test_no_sensitive_or_internal_keys(
    api_client_all: TestClient, method: str, endpoint: str, body: dict | None, skip_reason: str | None
):
    """Bất biến §7: Quét đệ quy GET profile, course-status, recommendations và POST recommendations, plan-check."""
    if skip_reason is not None:
        pytest.skip(skip_reason)

    forbidden_keys = {"fairness_group", "gender", "student_id", "curriculum_id", "course_id", "student_program_id"}

    def _check_forbidden(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                cur = f"{path}.{k}" if path else k
                assert k not in forbidden_keys, f"Phát hiện khóa bị cấm '{k}' tại '{cur}'"
                _check_forbidden(v, cur)
        elif isinstance(obj, list):
            for i, it in enumerate(obj):
                _check_forbidden(it, f"{path}[{i}]")

    if method == "GET":
        r = api_client_all.get(endpoint)
    else:
        r = api_client_all.post(endpoint, json=body)

    assert r.status_code == 200, f"{method} {endpoint} trả {r.status_code}"
    _check_forbidden(r.json(), path=f"{method} {endpoint}")


# =====================================================================
# 16. Test Bổ Sung Khớp Hợp Đồng & Mock Wiring (P5)
# =====================================================================

# Đúng những khóa `recommend()` trả (src/recommender/__init__.py): API tự thêm university_code, student_code,
# curriculum_code, term, algorithm_version.
MOCK_RECOMMENDATION_DICT = {
    "what_if": False,
    "weights": {
        "outstanding_retake": 3.0,
        "overdue": 2.0,
        "on_time": 2.0,
        "unlocks": 1.5,
        "strong_topic": 1.0,
        "interest": 0.5,
    },
    "candidate_count": 16,
    "items": [
        {
            "rank": 1,
            "course_code": "MAT2505",
            "course_name": "Lập trình cơ bản",
            "credits": 3,
            "block_code": "III",
            "status": "retake",
            "score": 3.0,
            "reasons": [
                {
                    "code": "outstanding_retake",
                    "contribution": 3.0,
                    "text": "Môn nợ cần học lại",
                    "data": {"attempt_no": 1},
                }
            ],
        }
    ],
    "not_eligible": [
        {
            "course_code": "MAT3533",
            "course_name": "Học máy",
            "credits": 3,
            "block_code": "V.1",
            "status": "missing_prerequisite",
            "missing_prerequisites": [["MAT2323"]],
            "text": "Chưa hoàn thành môn tiên quyết MAT2323",
        }
    ],
}


def test_fairness_stub(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Fairness §7: hai sinh viên chỉ khác fairness_group nhận cùng items;

    API không chuyển fairness_group vào recommend().
    """
    import src.recommender

    captured_calls = []

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        captured_calls.append({"student": student, "k": k, "weights": weights, "assumptions": assumptions})
        return copy.deepcopy(MOCK_RECOMMENDATION_DICT)

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)

    r1 = api_client_all.get("/v1/universities/HUS/students/T03/recommendations")
    assert r1.status_code == 200
    d1 = r1.json()

    # Kiểm tra API không đưa fairness_group vào bất kỳ tham số nào của recommend()
    assert len(captured_calls) >= 1
    call = captured_calls[-1]
    assert "fairness_group" not in call
    assert "fairness_group" not in (call.get("weights") or {})
    # Kiểm tra response không chứa fairness_group
    assert "fairness_group" not in d1
    for it in d1.get("items", []):
        assert "fairness_group" not in it


def test_assumptions_body_shape_validation_422(api_client_all: TestClient):
    """Kiểm tra hình dạng body của assumptions (schema, không cần tầng recommender) trả 422:

    - status lạ (ngoài passed, failed)
    - body có khóa lạ (extra='forbid')
    - assumption item có khóa lạ

    Nội dung assumptions (mã môn không thuộc khung, điểm ngoài thang) do apply_assumptions() của
    RANK-2 kiểm; API chỉ đổi ValueError thành 422 (xem test_recommend_value_error_becomes_422).
    """
    # 1. status lạ
    r4 = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"assumptions": [{"course_code": "MAT2505", "status": "invalid_status", "score": 8.0}]},
    )
    assert r4.status_code == 422
    assert r4.json()["error"]["code"] == "validation_error"

    # 2. body có khóa lạ (extra='forbid')
    r5 = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"extra_key_forbidden": "hello"},
    )
    assert r5.status_code == 422
    assert r5.json()["error"]["code"] == "validation_error"

    # 3. assumption item có khóa lạ
    r6 = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"assumptions": [{"course_code": "MAT2505", "status": "passed", "unknown_field": 123}]},
    )
    assert r6.status_code == 422
    assert r6.json()["error"]["code"] == "validation_error"


def test_weights_partial_merge(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """weights: gửi một phần thì merged_weights truyền xuống recommend() đã ghép đủ 6 khóa mặc định."""
    import src.recommender

    captured_weights = {}

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        nonlocal captured_weights
        captured_weights = weights
        resp = copy.deepcopy(MOCK_RECOMMENDATION_DICT)
        if weights:
            resp["weights"] = weights
        return resp

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)

    body = {"weights": {"outstanding_retake": 4.5}}
    r = api_client_all.post("/v1/universities/HUS/students/T03/recommendations", json=body)
    assert r.status_code == 200
    assert captured_weights is not None
    expected_keys = {"outstanding_retake", "overdue", "on_time", "unlocks", "strong_topic", "interest"}
    assert set(captured_weights.keys()) == expected_keys
    assert captured_weights["outstanding_retake"] == 4.5
    assert captured_weights["overdue"] == 2.0


def test_get_post_recommendations_parity(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """GET và POST /recommendations cùng cấu trúc, what_if = true đúng khi assumptions khác rỗng."""
    import src.recommender

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        resp = copy.deepcopy(MOCK_RECOMMENDATION_DICT)
        resp["what_if"] = bool(assumptions or skip or swap)
        return resp

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)

    # 1. GET
    r_get = api_client_all.get("/v1/universities/HUS/students/T03/recommendations")
    assert r_get.status_code == 200
    d_get = r_get.json()
    assert d_get["what_if"] is False

    # 2. POST không có assumptions -> what_if false
    r_post_empty = api_client_all.post("/v1/universities/HUS/students/T03/recommendations", json={})
    assert r_post_empty.status_code == 200
    d_post_empty = r_post_empty.json()
    assert d_post_empty["what_if"] is False

    # Cùng các khóa cấu trúc
    assert set(d_get.keys()) == set(d_post_empty.keys())

    # 3. POST có assumptions hợp lệ -> what_if true
    r_post_whatif = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 7.0}]},
    )
    assert r_post_whatif.status_code == 200
    assert r_post_whatif.json()["what_if"] is True


def test_plan_check_multi_violations_and_duplicates(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """plan-check: một học phần sinh nhiều vi phạm (stub check_plan trả 2 vi phạm cùng course_code),

    valid=false, và kiểm tra mã trùng trong course_codes vẫn được gửi đủ cho check_plan.
    """
    import src.explain
    import src.rules.plan

    received_course_codes = []

    def stub_check_plan(repo, student, course_codes):
        nonlocal received_course_codes
        received_course_codes = list(course_codes)
        return [
            {"code": "missing_prerequisite", "course_code": "MAT3533", "data": {"missing": ["MAT2323"]}},
            {"code": "duplicate_course", "course_code": "MAT3533", "data": {"count": 2}},
        ]

    monkeypatch.setattr(src.rules.plan, "check_plan", stub_check_plan)
    monkeypatch.setattr(src.explain, "violation_text", lambda v, c, names: f"Lỗi {v['code']}")

    body = {
        "term": "20261",
        "course_codes": ["MAT3533", "MAT3533"],
    }
    r = api_client_all.post("/v1/universities/HUS/students/T03/plan-check", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert len(data["violations"]) == 2
    assert all(v["course_code"] == "MAT3533" for v in data["violations"])
    assert data["violations"][0]["code"] == "missing_prerequisite"
    assert data["violations"][1]["code"] == "duplicate_course"
    # Kiểm tra check_plan nhận đúng course_codes gốc (không bị dedupe)
    assert received_course_codes == ["MAT3533", "MAT3533"]
    # Nhưng total_credits chỉ tính một lần cho MAT3533 (3 tín chỉ)
    assert data["total_credits"] == 3


def test_recommendations_wiring_stub(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """P5.6: Recommendations wiring bằng stub: monkeypatch recommend, kiểm 200 và schema,

    kiểm limit, weights, assumptions truyền đúng xuống recommend().
    """
    import src.recommender

    captured_args = {}

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        nonlocal captured_args
        captured_args = {
            "student_code": str(student["student_code"]),
            "k": k,
            "weights": weights,
            "assumptions": assumptions,
            "term_code": term_code,
            "year_of_study": int(student["year_of_study"]),
            "skip": skip,
            "swap": swap,
        }
        resp = copy.deepcopy(MOCK_RECOMMENDATION_DICT)
        resp["what_if"] = bool(assumptions or skip or swap)
        return resp

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)

    body = {
        "term": "20261",
        "limit": 7,
        "weights": {"unlocks": 2.5},
        "assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 8.0}],
        "skip": ["MAT2503"],
        "swap": [{"course_code": "HIS1056", "replacement": "HUS1024"}],
    }
    r = api_client_all.post("/v1/universities/HUS/students/T03/recommendations", json=body)
    assert r.status_code == 200
    data = r.json()
    # Kiểm schema
    assert data["university_code"] == "HUS"
    assert data["student_code"] == "T03"
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["term"] == "20261"
    assert data["algorithm_version"] == ALGORITHM_VERSION
    assert data["what_if"] is True  # do recommend() quyết định, kể cả khi chỉ có skip/swap
    assert isinstance(data["items"], list)
    assert isinstance(data["not_eligible"], list)
    assert isinstance(data["weights"], dict)

    # Kiểm tra các tham số truyền đúng xuống recommend()
    assert captured_args["student_code"] == "T03"
    assert captured_args["k"] == 7
    assert captured_args["weights"]["unlocks"] == 2.5
    assert len(captured_args["assumptions"]) == 1
    assert captured_args["assumptions"][0]["course_code"] == "MAT2505"
    assert captured_args["assumptions"][0]["status"] == "passed"
    assert captured_args["assumptions"][0]["score"] == 8.0
    # term đi xuống cả hai đường: sinh viên đọc theo kỳ đó và recommend() nhận term_code
    assert captured_args["term_code"] == "20261"
    assert captured_args["year_of_study"] == 2
    assert captured_args["skip"] == ["MAT2503"]
    assert captured_args["swap"] == [{"course_code": "HIS1056", "replacement": "HUS1024"}]


# =====================================================================
# 17. Bổ sung: limit trong OpenAPI, term, ValueError → 422, DB không đổi
# =====================================================================

def test_limit_bounds_documented_and_enforced(api_client_all: TestClient):
    """limit có ge=1, le=20 trong OpenAPI (GET và POST), không chỉ kiểm bằng tay."""
    spec = api_client_all.get("/openapi.json").json()
    path = "/v1/universities/{uni}/students/{student_code}/recommendations"
    get_limit = next(p for p in spec["paths"][path]["get"]["parameters"] if p["name"] == "limit")
    assert get_limit["schema"]["minimum"] == 1 and get_limit["schema"]["maximum"] == 20
    body_ref = spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    body_schema = spec["components"]["schemas"][body_ref.rsplit("/", 1)[1]]
    assert body_schema["properties"]["limit"]["minimum"] == 1
    assert body_schema["properties"]["limit"]["maximum"] == 20

    r = api_client_all.post(path.format(uni="HUS", student_code="T03"), json={"limit": 21})
    assert r.status_code == 422
    assert "limit" in r.json()["error"]["details"]["fields"]


def test_recommendations_term_reaches_student_and_recommend(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """`term` làm đổi cả sinh viên được đọc (year_of_study theo kỳ) lẫn `term_code` truyền cho recommend()."""
    import src.recommender

    seen = []

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        seen.append((term_code, int(student["year_of_study"])))
        return copy.deepcopy(MOCK_RECOMMENDATION_DICT)

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)
    r = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?term=20252")
    assert r.status_code == 200
    assert r.json()["term"] == "20252"
    assert seen == [("20252", 1)]  # T03 khóa 2025: kỳ 20252 vẫn là năm 1

    r404 = api_client_all.get("/v1/universities/HUS/students/T03/recommendations?term=99999")
    assert r404.status_code == 404 and r404.json()["error"]["code"] == "term_not_found"


def test_recommend_value_error_becomes_422(api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch):
    """ValueError từ recommend()/apply_assumptions() → 422 validation_error kèm details.fields."""
    import src.recommender

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        raise ValueError("assumptions[0].score: phải là số trong [0, 10], nhận được 99")

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)
    r = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 6.0}]},
    )
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert list(err["details"]["fields"]) == ["assumptions[0].score"]


@pytest.mark.parametrize(
    "body,message,field",
    [
        ({"skip": ["MAT2503"]}, "skip[0]: MAT2503 không gợi ý được ở học kỳ này", "skip[0]"),
        (
            {"swap": [{"course_code": "HIS1056", "replacement": "HUS1024"}]},
            "swap[0].replacement: HUS1024 làm khối tự chọn II không còn hoàn thành đúng số tín chỉ được",
            "swap[0].replacement",
        ),
        ({"skip": ["MAT2503"]}, "lỗi không có đường dẫn", "skip"),
    ],
)
def test_recommend_value_error_of_skip_and_swap_becomes_422(
    api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch, body: dict, message: str, field: str
):
    """ValueError do `skip` / `swap` sai → 422 validation_error, `details.fields` mang đúng đường dẫn trường."""
    import src.recommender

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        raise ValueError(message)

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)
    r = api_client_all.post("/v1/universities/HUS/students/T03/recommendations", json=body)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert list(err["details"]["fields"]) == [field]


def test_recommend_value_error_without_assumptions_is_not_422(
    api_client_all: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """ValueError từ recommend() khi KHÔNG có assumptions, skip hay swap là lỗi nội bộ (500), không giả làm 422.

    weights đã được kiểm bằng merge_weights() ở API, nên ValueError còn lại không phải lỗi đầu vào.
    """
    import src.recommender

    def stub_recommend(repo, student, k=5, weights=None, assumptions=None, term_code=None, skip=None, swap=None):
        raise ValueError("lỗi bên trong tầng xếp hạng")

    monkeypatch.setattr(src.recommender, "recommend", stub_recommend)
    r = api_client_all.get("/v1/universities/HUS/students/T03/recommendations")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "internal_error"
    assert "lỗi bên trong tầng xếp hạng" not in r.text


def test_assumptions_do_not_change_database(api_client_all: TestClient, repo_all):
    """§6 điểm 6, §7: what-if chỉ tính trong bộ nhớ, kết quả học tập trong DB không đổi."""
    before = repo_all.course_results().reset_index(drop=True)
    r = api_client_all.post(
        "/v1/universities/HUS/students/T03/recommendations",
        json={"assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 6.0}]},
    )
    assert r.status_code == 200 and r.json()["what_if"] is True
    after = repo_all.course_results().reset_index(drop=True)
    assert before.equals(after)

# =====================================================================
# 18. Ghép nối với các tầng thật (không stub): bắt lỗi chữ ký và lỗi dựng phản hồi
# =====================================================================

STUDENT_URL = "/v1/universities/HUS/students/{code}"


def test_student_endpoints_work_with_real_layers(api_client_all: TestClient):
    """5 endpoint sinh viên gọi tầng luật, xếp hạng, giải thích THẬT và trả 200 cho mọi sinh viên kiểm thử.

    Các test stub ở trên không bắt được lệch chữ ký giữa API và tầng dưới; test này bắt.
    """
    import pandas as pd

    expected = pd.read_csv(PROJECT_ROOT / "test" / "fixtures" / "students" / "expected_course_status.csv")
    for code in sorted(expected.loc[expected["university_code"] == "HUS", "student_code"].unique()):
        base = STUDENT_URL.format(code=code)
        for response in (
            api_client_all.get(f"{base}/profile"),
            api_client_all.get(f"{base}/course-status"),
            api_client_all.get(f"{base}/recommendations"),
            api_client_all.post(f"{base}/recommendations", json={}),
            api_client_all.post(f"{base}/plan-check", json={"course_codes": ["MAT2505", "MAT2505", "NOPE999"]}),
        ):
            assert response.status_code == 200, f"{code} {response.request.method} {response.request.url}: {response.text}"


def test_recommendations_carry_identity_and_algorithm_version(api_client_all: TestClient):
    """API chỉ thêm trường nhận dạng; `what_if`, `weights`, `candidate_count`, `items`, `not_eligible` do recommend()."""
    data = api_client_all.get(STUDENT_URL.format(code="T03") + "/recommendations?term=20261").json()
    assert data["university_code"] == "HUS"
    assert data["student_code"] == "T03"
    assert data["curriculum_code"] == "HUS-7480113QTD-2022"
    assert data["term"] == "20261"
    assert data["algorithm_version"] == ALGORITHM_VERSION
    assert data["what_if"] is False
    assert data["candidate_count"] >= len(data["items"])


def test_term_changes_recommendations_course_status_and_profile(api_client_all: TestClient):
    """`?term=` đổi kết quả thật: sinh viên khóa 2023 ở kỳ 20251 khác hẳn ở kỳ mặc định 20261."""
    base = STUDENT_URL.format(code="23000001")

    def codes(url: str) -> list[str]:
        return [item["course_code"] for item in api_client_all.get(url).json()["items"]]

    assert codes(f"{base}/recommendations?term=20251") != codes(f"{base}/recommendations")

    p_old = api_client_all.get(f"{base}/profile?term=20251").json()
    p_new = api_client_all.get(f"{base}/profile").json()
    assert (p_old["year_of_study"], p_new["year_of_study"]) == (3, 4)
    assert p_old["target_semester"] < p_new["target_semester"]
    assert p_old["credits_earned"] <= p_new["credits_earned"]

    s_old = api_client_all.get(f"{base}/course-status?term=20251").json()["summary"]
    s_new = api_client_all.get(f"{base}/course-status").json()["summary"]
    assert s_old != s_new


def test_skip_and_swap_change_items_and_set_what_if(api_client_all: TestClient):
    """`skip` và `swap` đi tới recommend(): môn bị bỏ vắng mặt, `what_if` do recommend() trả là true."""
    url = STUDENT_URL.format(code="23000001") + "/recommendations"
    base = api_client_all.post(url, json={}).json()
    assert base["what_if"] is False
    first, second = base["items"][0]["course_code"], base["items"][1]["course_code"]

    skipped = api_client_all.post(url, json={"skip": [first]})
    assert skipped.status_code == 200
    assert skipped.json()["what_if"] is True
    assert first not in [i["course_code"] for i in skipped.json()["items"]]
    assert skipped.json()["candidate_count"] == base["candidate_count"]

    swapped = api_client_all.post(url, json={"swap": [{"course_code": second, "replacement": base["items"][-1]["course_code"]}]})
    assert swapped.status_code == 200
    assert swapped.json()["what_if"] is True


@pytest.mark.parametrize(
    "body,field",
    [
        ({"skip": ["MAT9999"]}, "skip[0]"),
        ({"swap": [{"course_code": "MAT9999", "replacement": "MAT9998"}]}, "swap[0].course_code"),
        ({"assumptions": [{"course_code": "MAT9999", "status": "passed"}]}, "assumptions[0].course_code"),
        ({"assumptions": [{"course_code": "MAT2505", "status": "passed", "score": 99}]}, "assumptions[0].score"),
    ],
)
def test_invalid_choices_are_422_with_field_path(api_client_all: TestClient, body: dict, field: str):
    """Nội dung `assumptions` / `skip` / `swap` sai do tầng xếp hạng phát hiện → 422, khóa là đường dẫn trường."""
    r = api_client_all.post(STUDENT_URL.format(code="T03") + "/recommendations", json=body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "validation_error"
    assert list(r.json()["error"]["details"]["fields"]) == [field]


def test_plan_check_texts_come_from_explain_layer(api_client_all: TestClient):
    """plan-check dùng check_plan() và violation_text() thật: mỗi vi phạm có câu tiếng Việt nêu tên môn."""
    r = api_client_all.post(
        STUDENT_URL.format(code="T03") + "/plan-check",
        json={"term": "20261", "course_codes": ["MAT3533", "MAT3533"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert {v["code"] for v in data["violations"]} >= {"missing_prerequisite", "duplicate_course"}
    for violation in data["violations"]:
        assert violation["text"] and "Học máy" in violation["text"]
