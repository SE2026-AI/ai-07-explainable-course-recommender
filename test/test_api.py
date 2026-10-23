"""Kiểm thử tự động 8 endpoint API v1 cốt lõi theo hợp đồng api-contract.md."""
from __future__ import annotations

import ast
import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.deps import get_repo
from src.recommender import ALGORITHM_VERSION


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

def test_health(api_client: TestClient):
    """GET /v1/health trả 200, không bọc meta."""
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
    project_root = pathlib.Path(__file__).resolve().parents[1]
    committed_path = project_root / "docs" / "api" / "openapi.json"
    assert committed_path.exists(), "docs/api/openapi.json chưa tồn tại"

    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    current = create_app().openapi()

    def _normalize(spec: dict) -> dict:
        # Chuẩn hóa khác biệt giữa Pydantic 2.9 (không có additionalProperties) và Pydantic 2.10+ (có additionalProperties: True)
        import copy

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

def test_bug5_no_inapplicable_nulls_in_catalog_and_system(api_client_all: TestClient):
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


def test_bug6_no_sql_outside_data_layer():
    """Lỗi 6: SQL trong tầng API (_q / SELECT ngoài src/data/).

    Quét AST mọi file .py dưới src/api/, src/rules/, src/recommender/, src/explain/:
    Khẳng định KHÔNG có lời gọi _q( và KHÔNG có chuỗi 'SELECT ' (bỏ qua docstring/comment).
    """
    project_root = pathlib.Path(__file__).resolve().parents[1]
    dirs_to_check = ["src/api", "src/rules", "src/recommender", "src/explain"]

    violations = []

    for d in dirs_to_check:
        dir_path = project_root / d
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
                            f"{py_file.relative_to(project_root)}:{node.lineno}: Gọi hàm nội bộ '_q'"
                        )

                # 2. Kiểm tra chuỗi chứa 'SELECT ' ngoài docstring
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node not in docstring_nodes
                    and "SELECT " in node.value.upper()
                ):
                    violations.append(
                        f"{py_file.relative_to(project_root)}:{node.lineno}: Chứa chuỗi SQL '{node.value.strip()[:40]}...'"
                    )

    assert not violations, "Phát hiện SQL / _q vi phạm kiến trúc data-model:\n" + "\n".join(violations)


def test_bug7_openapi_enums_enforced():
    """Lỗi 7: Khóa hợp đồng bằng kiểu dữ liệu (Literal enums + xuất lại OpenAPI).

    Đọc docs/api/openapi.json và khẳng định các trường enum được khai báo chính xác.
    """
    project_root = pathlib.Path(__file__).resolve().parents[1]
    openapi_path = project_root / "docs" / "api" / "openapi.json"
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

