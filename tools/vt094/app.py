"""Plan-check characterization scaffold, before VT-094 notification implementation."""
from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.api.errors import register_handlers
from src.api.routers.recommendations import post_plan_check
from src.api.schemas.recommendations import PlanCheckBodyIn


class SyntheticRepo:
    """Deterministic repository double: 100 courses, real rules and API assembly."""
    def __init__(self):
        self.courses = pd.DataFrame([
            {"course_code": f"C{i:03}", "course_name": f"Synthetic {i}", "credits": 3,
             "block_code": "CORE", "elective_block": None, "prerequisite_groups": [],
             "counts_toward_total": True} for i in range(100)
        ])

    def universities(self):
        return pd.DataFrame([{"university_code": "HUS"}])

    def student_programs(self, uni, code):
        rows = [{"is_primary": True, "status": "active"}] if (uni, code) == ("HUS", "T03") else []
        return pd.DataFrame(rows)

    def setting(self, key):
        return "20261"

    def terms(self, uni):
        return pd.DataFrame([{"term_code": "20261"}])

    def student(self, uni, code, term):
        return pd.Series({"university_code": uni, "student_code": code,
                          "curriculum_code": "SYNTHETIC", "passed_courses": []})

    def curriculum(self, code):
        return {"max_credits_per_term": 24}

    def curriculum_courses(self, code):
        return self.courses.copy(deep=True)

    def blocks(self, code):
        return pd.DataFrame([{"block_code": "CORE", "counts_toward_total": True}])

    def elective_blocks(self, code):
        return pd.DataFrame(columns=["block_code", "required_credits"])


class Input(BaseModel):
    course_codes: list[str]


class Audit:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, result TEXT NOT NULL)")

    def save(self, result):
        with sqlite3.connect(self.path, timeout=3) as conn:
            cursor = conn.execute("INSERT INTO checks(result) VALUES (?)", (json.dumps(result),))
            return cursor.lastrowid

    def rows(self):
        with sqlite3.connect(self.path) as conn:
            return [(i, json.loads(body)) for i, body in conn.execute("SELECT id,result FROM checks ORDER BY id")]


def create_app(db_path: Path, sender=None, repo=None, queue_size=128, send_timeout=.05):
    audit = Audit(db_path)
    repo = repo if repo is not None else SyntheticRepo()

    @asynccontextmanager
    async def lifespan(app):
        yield

    app = FastAPI(lifespan=lifespan)
    register_handlers(app)
    app.state.audit = audit

    def primary(body):
        result = post_plan_check("HUS", "T03", PlanCheckBodyIn(course_codes=body.course_codes), repo)
        response = result.model_dump()
        audit.save(response)
        return response

    @app.post('/experiment/plan-check')
    async def plan_check(body: Input):
        return await run_in_threadpool(primary, body)

    return app
