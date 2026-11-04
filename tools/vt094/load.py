"""Real loopback HTTP experiment with 100 closed-loop workers; no SMTP/Postgres required."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

import httpx
import uvicorn

from tools.vt094.app import create_app


def serve(args):
    async def slow_sender(event):
        await asyncio.Event().wait()

    app = create_app(Path(args.db), sender=slow_sender if args.mode == 'slow' else None)

    @app.get('/experiment/diagnostics')
    async def diagnostics():
        n = app.state.notifier
        return {'sent': n.sent, 'failed': n.failed, 'dropped': n.dropped, 'queued': n.queue.qsize()}

    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='critical', access_log=False)


async def phase(client, name, codes, expected_status, expected_total, attempts=3):
    gate = asyncio.Event()
    records = []

    async def worker(number):
        await gate.wait()
        for index in range(attempts):
            started = time.perf_counter()
            status = 0
            error = ''
            try:
                response = await client.post('/experiment/plan-check', json={'course_codes': codes})
                status = response.status_code
                data = response.json()
                correct = status == expected_status
                if status == 200:
                    correct = correct and data['student_code'] == 'T03' and data['university_code'] == 'HUS'
                    correct = correct and data['total_credits'] == expected_total and data['max_credits_per_term'] == 24
                    correct = correct and data['valid'] == (expected_total <= 24)
                elif status == 422:
                    correct = correct and data['error']['code'] == 'validation_error'
            except Exception as exc:
                correct = False
                error = type(exc).__name__
            records.append({'phase': name, 'worker': number, 'iteration': index,
                            'elapsed_ms': (time.perf_counter()-started)*1000,
                            'status': status, 'correct': correct, 'error': error})

    tasks = [asyncio.create_task(worker(i)) for i in range(100)]
    start = time.perf_counter()
    gate.set()
    await asyncio.gather(*tasks)
    duration = time.perf_counter()-start
    values = sorted(r['elapsed_ms'] for r in records)
    p95 = values[math.ceil(.95*len(values))-1]
    return records, {'name': name, 'workers': 100, 'attempts': len(records),
                     'correct': sum(r['correct'] for r in records), 'p95_ms': p95,
                     'max_ms': max(values), 'duration_s': duration,
                     'p95_target_met': p95 <= 3000, 'expected_status': expected_status,
                     'sender': 'never completes;50ms cooperative timeout' if name == 'slow_sender' else 'local no-op'}


def count(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute('SELECT COUNT(*) FROM checks').fetchone()[0]


async def run(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    Path('.vt094-tmp').mkdir(exist_ok=True)
    summaries, all_records = [], []
    for mode in ['fast', 'slow']:
        with tempfile.TemporaryDirectory(prefix='load-', dir='.vt094-tmp') as tmp:
            db = str(Path(tmp)/'audit.db')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            with (output/f'load-server-{mode}.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen([sys.executable, '-m', 'tools.vt094.load', '--serve',
                                            '--mode', mode, '--db', db, '--port', str(port)],
                                           stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    limits = httpx.Limits(max_connections=100, max_keepalive_connections=100)
                    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}', timeout=30,
                                                 limits=limits, trust_env=False) as client:
                        for _ in range(200):
                            try:
                                if (await client.get('/experiment/diagnostics')).status_code == 200:
                                    break
                            except httpx.TransportError:
                                pass
                            if process.poll() is not None:
                                raise RuntimeError('server exited before readiness')
                            await asyncio.sleep(.05)
                        else:
                            raise RuntimeError('server readiness deadline exceeded')
                        # Warm10 are excluded from workload counts and row deltas.
                        for _ in range(10):
                            response = await client.post('/experiment/plan-check', json={'course_codes': ['C000']})
                            assert response.status_code == 200
                        plans = [('small', ['C000'], 200, 3),
                                 ('largest_accepted', [f'C{i:03}' for i in range(100)], 200, 300),
                                 ('oversized_rejected', ['C000']*10000, 422, 0)] if mode == 'fast' else [
                                     ('slow_sender', ['C000'], 200, 3)]
                        for name, codes, expected, total in plans:
                            before = count(db)
                            records, summary = await phase(client, name, codes, expected, total)
                            after = count(db)
                            summary['audit_row_delta'] = after-before
                            summary['expected_audit_delta'] = summary['correct'] if expected == 200 else 0
                            summary['audit_matches'] = after-before == summary['expected_audit_delta']
                            summary['notification_snapshot'] = (await client.get('/experiment/diagnostics')).json()
                            summaries.append(summary)
                            all_records.extend(records)
                            print(json.dumps(summary), flush=True)
                finally:
                    process.terminate()
                    process.wait(timeout=10)
    result = {'date': '2026-11-04', 'platform': platform.platform(), 'python': platform.python_version(),
              'cpu_logical': os.cpu_count(), 'httpx': httpx.__version__, 'uvicorn': uvicorn.__version__,
              'protocol': ('100 closed-loop HTTP workers x3 requests/phase;nearest-rank p95 all attempts;'
                           '30s timeout;10 warm/server'),
              'scope': ('real loopback HTTP,actual project domain/API assembly,synthetic repository100 courses,'
                        'SQLite commit,local sender double;not PostgreSQL/SMTP/production'),
              'limits': ('same-host client/server;single Uvicorn worker;SQLite lock/CPU/client queuing included;'
                         'short experiment;no production guarantee'),
              'phases': summaries}
    (output/'load-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (output/'load-requests.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_records[0]))
        writer.writeheader()
        writer.writerows(all_records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--mode', default='fast')
    parser.add_argument('--db')
    parser.add_argument('--port', type=int, default=18894)
    parser.add_argument('--output', default='docs/tasks/VT-094/evidence')
    args = parser.parse_args()
    if args.serve:
        serve(args)
    else:
        asyncio.run(run(args))
