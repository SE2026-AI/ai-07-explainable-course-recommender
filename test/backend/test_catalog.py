"""T-03 Catalog integrity (Q-02): invalid snapshots are rejected before any eligibility claim."""

import pytest

from backend.domain.catalog import CatalogInvalid, CatalogVersionUnknown, build_snapshot
from conftest import REFERENCE


def _raw(courses, goals=None):
    return {"catalog_version": "t", "goals": goals or {}, "courses": courses}


def _course(cid, prereqs=(), **kw):
    return {"course_id": cid, "title": cid, "credits": 3, "mandatory_prerequisites": list(prereqs), **kw}


def test_bundled_catalogs_load(repo):
    assert repo.versions == ["catalog-demo-v1", "catalog-synthetic-v1"]


def test_demo_catalog_matches_reference_fixture(demo):
    for ref in REFERENCE["courses"]:
        course = demo.courses[ref["course_id"]]
        assert course.credits == ref["credits"]
        assert list(course.mandatory_prerequisites) == ref["prerequisites"]
        assert course.workload_hours_per_week == ref["workload"]


@pytest.mark.parametrize("courses, fragment", [
    ([_course("A"), _course("A")], "duplicate"),
    ([_course("A", ["Z"])], "unknown course Z"),
    ([_course("A", ["B"]), _course("B", ["C"]), _course("C", ["A"])], "cycle"),
    ([_course("A", ["A"])], "itself"),
    ([_course("A", credits=0)], "credits"),
    ([_course("A", workload_hours_per_week=-1)], "workload"),
    ([_course("a")], "invalid course_id"),
    ([_course("A", goal_relevance={"NOPE": 0.5})], "unknown goal"),
])
def test_invalid_snapshot_rejected(courses, fragment):
    with pytest.raises(CatalogInvalid) as exc:
        build_snapshot(_raw(courses))
    assert fragment in str(exc.value)


def test_edges_point_prerequisite_to_dependent(demo):
    assert ("ST201", "AI301") in demo.edges()
    assert ("AI301", "DL401") in demo.edges()


def test_unknown_version(repo):
    with pytest.raises(CatalogVersionUnknown):
        repo.get("catalog-old")
