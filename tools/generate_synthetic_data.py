"""Generate deterministic synthetic catalog, profiles and fairness cohort labels for AI-07.

Usage:
    python tools/generate_synthetic_data.py --seed 42 --profiles 300 --out tools/out

Outputs (all synthetic, no real student data):
    catalog.json   CatalogSnapshot-like object; courses follow the CatalogCourse schema plus goal/skill tags.
    goals.json     career goal -> course tag mapping (separate versioned artifact, see RECOMMENDER_DESIGN.md).
    profiles.json  list of Profile objects valid against contracts/openapi.yaml#/components/schemas/Profile.
    cohorts.json   profile_id -> group labels used ONLY by fairness checks (never sent to the API).

Policies used are the fixture proposals (grade 0-10, pass >= 5, AND prerequisites passed in an earlier term).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

CATALOG_VERSION = "catalog-synthetic-v1"
GENERATOR_VERSION = "synthetic-gen-0.1"
PASSING_GRADE = 5
TERMS = ["T1", "T2", "T3"]

# course_id, title, credits, hours/week, mandatory prerequisites, recommended preparation, goal tags, skill tags
# The first six courses match docs/tasks/prompts/fixtures/reference-scenarios.json.
COURSES = [
    ("CS101", "Introduction to Programming", 3, 4, [], [], ["SWE", "ML_ENGINEER", "DATA_ANALYST"], ["PROGRAMMING"]),
    ("MA101", "Calculus I", 3, 5, [], [], ["ML_ENGINEER", "DATA_ANALYST"], ["MATH"]),
    ("ST201", "Probability and Statistics", 3, 6, ["MA101"], [], ["ML_ENGINEER", "DATA_ANALYST"], ["MATH", "DATA"]),
    ("SE201", "Software Engineering Fundamentals", 3, 4, ["CS101"], [], ["SWE"], ["PROGRAMMING", "PROCESS"]),
    ("AI301", "Artificial Intelligence", 4, 8, ["CS101", "ST201"], ["MA102"], ["ML_ENGINEER"], ["AI", "DATA"]),
    ("DL401", "Deep Learning", 4, 9, ["AI301"], ["MA201"], ["ML_ENGINEER"], ["AI"]),
    ("MA102", "Calculus II", 3, 5, ["MA101"], [], ["ML_ENGINEER"], ["MATH"]),
    ("MA201", "Linear Algebra", 3, 5, ["MA101"], [], ["ML_ENGINEER", "DATA_ANALYST"], ["MATH"]),
    ("CS102", "Object-Oriented Programming", 3, 5, ["CS101"], [], ["SWE"], ["PROGRAMMING"]),
    ("CS201", "Data Structures and Algorithms", 4, 7, ["CS102"], ["MA101"], ["SWE", "ML_ENGINEER"], ["PROGRAMMING", "ALGORITHMS"]),
    ("CS202", "Databases", 3, 5, ["CS101"], [], ["SWE", "DATA_ANALYST"], ["DATA"]),
    ("CS203", "Computer Networks", 3, 5, ["CS101"], [], ["SWE", "SECURITY"], ["SYSTEMS"]),
    ("CS204", "Operating Systems", 3, 6, ["CS102"], [], ["SWE", "SECURITY"], ["SYSTEMS"]),
    ("SE301", "Software Testing", 3, 4, ["SE201"], ["CS102"], ["SWE"], ["PROCESS", "QUALITY"]),
    ("SE302", "Web Application Development", 3, 6, ["CS202", "SE201"], [], ["SWE"], ["WEB", "PROGRAMMING"]),
    ("SE303", "Mobile Application Development", 3, 6, ["CS102"], ["SE201"], ["SWE"], ["MOBILE", "PROGRAMMING"]),
    ("DA301", "Data Visualization", 3, 4, ["ST201"], ["CS202"], ["DATA_ANALYST"], ["DATA", "VISUALIZATION"]),
    ("DA302", "Data Mining", 3, 6, ["ST201", "CS202"], [], ["DATA_ANALYST", "ML_ENGINEER"], ["DATA", "AI"]),
    ("ML302", "Machine Learning", 4, 8, ["ST201", "MA201", "CS101"], ["MA102"], ["ML_ENGINEER", "DATA_ANALYST"], ["AI", "MATH"]),
    ("NLP401", "Natural Language Processing", 3, 7, ["ML302"], ["DL401"], ["ML_ENGINEER"], ["AI", "LANGUAGE"]),
    ("SEC301", "Information Security", 3, 5, ["CS203"], ["CS204"], ["SECURITY"], ["SECURITY", "SYSTEMS"]),
    ("SEC401", "Network Security", 3, 6, ["SEC301"], [], ["SECURITY"], ["SECURITY"]),
    ("PM301", "Software Project Management", 3, 3, ["SE201"], [], ["SWE"], ["PROCESS"]),
    ("HU101", "Technical Writing", 2, 3, [], [], ["SWE", "DATA_ANALYST", "ML_ENGINEER", "SECURITY"], ["COMMUNICATION"]),
]

GOALS = {
    "ML_ENGINEER": {"title": "Machine Learning Engineer", "skill_tags": ["AI", "MATH", "DATA", "PROGRAMMING"]},
    "DATA_ANALYST": {"title": "Data Analyst", "skill_tags": ["DATA", "VISUALIZATION", "MATH"]},
    "SWE": {"title": "Software Engineer", "skill_tags": ["PROGRAMMING", "PROCESS", "WEB", "QUALITY"]},
    "SECURITY": {"title": "Security Engineer", "skill_tags": ["SECURITY", "SYSTEMS"]},
}
INTERESTS = sorted({tag for course in COURSES for tag in course[7]})

# Grade ranges per academic pattern: (min passing grade, max grade, failure probability per course).
PATTERNS = {
    "strong": (7.0, 10.0, 0.0),
    "average": (5.0, 8.5, 0.0),
    "has_failed": (5.0, 8.0, 0.25),
}


def build_catalog() -> dict:
    courses = []
    for cid, title, credits, hours, prereq, prep, goals, skills in COURSES:
        courses.append({
            "course_id": cid,
            "title": title,
            "credits": credits,
            "workload_hours_per_week": hours,
            "mandatory_prerequisites": prereq,
            "recommended_preparation": prep,
            "available_terms": list(TERMS),
            "career_goals": goals,
            "skills": skills,
        })
    validate_catalog(courses)
    return {
        "catalog_version": CATALOG_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source": "synthetic",
        "status": "illustrative_not_approved_contract",
        "courses": courses,
    }


def validate_catalog(courses: list[dict]) -> None:
    """Reject duplicate IDs, dangling references and prerequisite cycles."""
    ids = [c["course_id"] for c in courses]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate course_id in catalog")
    known = set(ids)
    for c in courses:
        for ref in c["mandatory_prerequisites"] + c["recommended_preparation"]:
            if ref not in known:
                raise ValueError(f"{c['course_id']} references unknown course {ref}")
    prereqs = {c["course_id"]: c["mandatory_prerequisites"] for c in courses}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(cid: str) -> None:
        if state.get(cid) == 1:
            raise ValueError(f"prerequisite cycle through {cid}")
        if state.get(cid) == 2:
            return
        state[cid] = 1
        for p in prereqs[cid]:
            visit(p)
        state[cid] = 2

    for cid in ids:
        visit(cid)


def simulate_history(rng: random.Random, pattern: str, terms_done: int, catalog: list[dict]) -> list[dict]:
    """Take courses term by term; a course is taken only when all prerequisites were passed in earlier terms."""
    low, high, fail_p = PATTERNS[pattern]
    passed: set[str] = set()
    history: list[dict] = []
    taken: set[str] = set()
    for term_index in range(terms_done):
        term_id = f"Y{term_index // 2 + 1}S{term_index % 2 + 1}"
        eligible = [c for c in catalog if c["course_id"] not in taken
                    and all(p in passed for p in c["mandatory_prerequisites"])]
        rng.shuffle(eligible)
        load, passed_this_term = 0, []
        for course in eligible:
            if load + course["credits"] > 12:
                continue
            load += course["credits"]
            taken.add(course["course_id"])
            if rng.random() < fail_p:
                grade, state = round(rng.uniform(2.0, PASSING_GRADE - 0.5), 1), "failed"
            else:
                grade, state = round(rng.uniform(low, high), 1), "passed"
                passed_this_term.append(course["course_id"])
            history.append({"course_id": course["course_id"], "state": state, "grade": grade, "completed_term": term_id})
        passed.update(passed_this_term)  # only usable as prerequisite from the next term on
    if pattern == "has_failed" and not any(h["state"] == "failed" for h in history) and history:
        victim = rng.choice(history)
        victim.update(state="failed", grade=round(rng.uniform(2.0, PASSING_GRADE - 0.5), 1))
        history = drop_invalid_dependents(history, catalog)
    return history


def drop_invalid_dependents(history: list[dict], catalog: list[dict]) -> list[dict]:
    """After forcing a failure, remove later passes whose prerequisites are no longer passed earlier."""
    prereqs = {c["course_id"]: c["mandatory_prerequisites"] for c in catalog}
    kept: list[dict] = []
    passed_before: dict[str, str] = {}
    for record in sorted(history, key=lambda h: h["completed_term"]):
        ok = all(p in passed_before and passed_before[p] < record["completed_term"] for p in prereqs[record["course_id"]])
        if not ok:
            continue
        kept.append(record)
        if record["state"] == "passed":
            passed_before[record["course_id"]] = record["completed_term"]
    return kept


def build_profiles(rng: random.Random, count: int, catalog: list[dict]) -> tuple[list[dict], dict]:
    profiles, cohorts = [], {}
    pattern_names = list(PATTERNS)
    for i in range(1, count + 1):
        pid = f"SYN-{i:04d}"
        pattern = pattern_names[(i - 1) % len(pattern_names)]
        min_terms = 1 if pattern == "has_failed" else 0  # a failure needs at least one completed term
        history = simulate_history(rng, pattern, rng.randint(min_terms, 4), catalog)
        goals = rng.sample(sorted(GOALS), k=rng.choice([1, 1, 2]))
        profiles.append({
            "profile_id": pid,
            "history": history,
            "career_goal_ids": goals,
            "interest_ids": rng.sample(INTERESTS, k=rng.randint(1, 3)),
            "workload_preference": {
                "hours_per_week_budget": rng.choice([8, 10, 12, 15, 20]),
                "direction": rng.choice(["lower", "neutral", "higher"]),
            },
            "max_credits_per_term": rng.choice([6, 9, 12, 15]),
            "excluded_course_ids": [],
        })
        # Sensitive labels are drawn independently of history so any score gap is a defect, not data.
        cohorts[pid] = {
            "gender": rng.choice(["F", "M", "X"]),
            "region": rng.choice(["urban", "rural"]),
            "academic_pattern": pattern,
        }
    return profiles, cohorts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--profiles", type=int, default=300)
    parser.add_argument("--out", type=Path, default=Path("tools/out"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    catalog = build_catalog()
    profiles, cohorts = build_profiles(rng, args.profiles, catalog["courses"])
    meta = {"generator_version": GENERATOR_VERSION, "seed": args.seed, "catalog_version": CATALOG_VERSION}

    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "catalog.json": catalog,
        "goals.json": {**meta, "goals": GOALS},
        "profiles.json": {**meta, "profiles": profiles},
        "cohorts.json": {**meta, "usage": "fairness checks only; never send to API", "cohorts": cohorts},
    }
    for name, payload in outputs.items():
        (args.out / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog['courses'])} courses and {len(profiles)} profiles to {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()
