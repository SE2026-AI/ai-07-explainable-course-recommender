"""Isolated VT-094 plan-check + best-effort notification experiment, not public v1."""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
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
    model_config = ConfigDict(extra='forbid')
    course_codes: list[Annotated[str, StringConstraints(min_length=1, max_length=32)]] = Field(min_length=1, max_length=100)


class Notifier:
    """One cooperative async transport call at a time; queue overflow never touches audit."""
    def __init__(self, sender, queue_size=128, timeout=.05):
        if queue_size < 1 or timeout <= 0:
            raise ValueError('queue_size and timeout must be positive')
        self.sender = sender
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.timeout = timeout
        self.sent = self.failed = self.dropped = 0

    def offer(self, event):
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1
            logging.getLogger(__name__).warning('notification_queue_full')
            return False
        return True

    async def run(self):
        while True:
            event = await self.queue.get()
            try:
                await asyncio.wait_for(self.sender(event), timeout=self.timeout)
                self.sent += 1
            except Exception:
                self.failed += 1
                logging.getLogger(__name__).warning('notification_send_failed', exc_info=True)
            finally:
                self.queue.task_done()


async def local_sender(event):
    """Synthetic transport: no external recipient or network side effect."""
    return None


class Audit:
    def __init__(self, path):
        self.path = str(path)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, result TEXT NOT NULL)")

    def save(self, result):
        with closing(sqlite3.connect(self.path, timeout=3)) as conn, conn:
            cursor = conn.execute("INSERT INTO checks(result) VALUES (?)", (json.dumps(result),))
            return cursor.lastrowid

    def rows(self):
        with closing(sqlite3.connect(self.path)) as conn:
            return [(i, json.loads(body)) for i, body in conn.execute("SELECT id,result FROM checks ORDER BY id")]


def create_app(db_path: Path, sender=None, repo=None, queue_size=128, send_timeout=.05):
    audit = Audit(db_path)
    repo = repo if repo is not None else SyntheticRepo()
    notifier = Notifier(sender if sender is not None else local_sender, queue_size, send_timeout)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(notifier.run())
        try:
            yield
        finally:
            # shortcut: best-effort queue loses pending events on exit; use durable delivery if required.
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    app = FastAPI(lifespan=lifespan)
    register_handlers(app)
    app.state.audit = audit
    app.state.notifier = notifier

    def primary(body):
        result = post_plan_check("HUS", "T03", PlanCheckBodyIn(course_codes=body.course_codes), repo)
        response = result.model_dump()
        response['student_code'] = result.university_code
        check_id = audit.save(response)
        return check_id, response

    @app.post('/experiment/plan-check')
    async def plan_check(body: Input):
        check_id, response = await run_in_threadpool(primary, body)
        notifier.offer({'event': 'PlanChecked', 'check_id': check_id,
                        'valid': response['valid'], 'course_count': len(body.course_codes)})
        return response

    return app
