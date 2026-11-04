"""VT-094 independent oracles; real FastAPI, SQLite and project plan-check logic."""
import asyncio
import sqlite3

import pytest
from fastapi.testclient import TestClient

from tools.vt094 import app as vt


def drain(client, app):
    if hasattr(app.state, 'notifier'):
        client.portal.call(app.state.notifier.queue.join)


def test_t01_response_mapping_and_committed_event(tmp_path):
    observed = []
    app = None

    async def send(event):
        # A separate SQLite connection must see commit BEFORE delivery.
        observed.append((event, app.state.audit.rows()))

    app = vt.create_app(tmp_path/'audit.db', sender=send)
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        drain(client, app)
    expected = {'university_code': 'HUS', 'student_code': 'T03', 'term': '20261',
                'total_credits': 3, 'max_credits_per_term': 24, 'valid': True, 'violations': []}
    assert response.status_code == 200
    assert response.json() == expected
    assert len(observed) == 1, 'completed transaction must notify exactly once in this execution'
    event, rows = observed[0]
    assert rows == [(1, expected)]
    assert event == {'event': 'PlanChecked', 'check_id': 1, 'valid': True, 'course_count': 1}


def test_t02_sender_error_does_not_undo_commit(tmp_path):
    async def send(event):
        raise OSError('synthetic transport failure')
    app = vt.create_app(tmp_path/'audit.db', sender=send)
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        drain(client, app)
    assert response.status_code == 200 and response.json()['valid'] is True
    assert len(app.state.audit.rows()) == 1
    assert hasattr(app.state, 'notifier'), 'missing failure-isolated notification worker'
    assert app.state.notifier.failed == 1


def test_t03_sender_timeout_does_not_hold_main_request(tmp_path):
    async def send(event):
        await asyncio.Event().wait()
    app = vt.create_app(tmp_path/'audit.db', sender=send, send_timeout=.01)
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        drain(client, app)
    assert response.status_code == 200 and len(app.state.audit.rows()) == 1
    assert hasattr(app.state, 'notifier'), 'missing bounded sender timeout'
    assert app.state.notifier.failed == 1


@pytest.mark.parametrize('codes', [[], ['C000']*101, ['X'*33], [None], 'C000'],
                         ids=['empty', 'large101', 'code33', 'null-code', 'wrong-list-type'])
def test_t04_invalid_partition_rejected_before_db(tmp_path, codes):
    app = vt.create_app(tmp_path/'audit.db')
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': codes})
    assert response.status_code == 422
    assert app.state.audit.rows() == []


def test_t05_oversized_input_never_queries_repository(tmp_path):
    class RejectRepo:
        def universities(self):
            raise AssertionError('oversized input reached domain/repository')
    app = vt.create_app(tmp_path/'audit.db', repo=RejectRepo())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']*10000})
    assert response.status_code == 422
    assert app.state.audit.rows() == []


@pytest.mark.parametrize('codes,violation', [(['UNKNOWN'], 'not_in_curriculum'),
                                          (['C000','C000'], 'duplicate_course')])
def test_t06_invalid_business_plan_still_has_completed_event(tmp_path, codes, violation):
    events = []
    async def send(event):
        events.append(event)
    app = vt.create_app(tmp_path/'audit.db', sender=send)
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': codes})
        drain(client, app)
    assert response.status_code == 200 and response.json()['valid'] is False
    assert violation in [x['code'] for x in response.json()['violations']]
    assert len(events) == 1 and events[0]['valid'] is False


def test_t07_upper_partition_100_preserves_result_and_small_event(tmp_path):
    events = []
    async def send(event):
        events.append(event)
    app = vt.create_app(tmp_path/'audit.db', sender=send)
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': [f'C{i:03}' for i in range(100)]})
        drain(client, app)
    assert response.status_code == 200
    assert response.json()['total_credits'] == 300
    assert response.json()['max_credits_per_term'] == 24
    assert len(events) == 1 and events[0]['course_count'] == 100
    assert 'course_codes' not in events[0]


def test_t08_main_commit_failure_never_notifies(tmp_path, monkeypatch):
    events = []
    async def send(event):
        events.append(event)
    app = vt.create_app(tmp_path/'audit.db', sender=send)
    def fail(result):
        raise sqlite3.OperationalError('synthetic disk failure')
    monkeypatch.setattr(app.state.audit, 'save', fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        drain(client, app)
    assert response.status_code == 500 and events == []
    assert app.state.audit.rows() == []


def test_t09_queue_full_is_bounded():
    assert hasattr(vt, 'Notifier'), 'bounded notification queue is not implemented'
    async def scenario():
        async def send(event):
            return None
        notifier = vt.Notifier(send, queue_size=1, timeout=.01)
        assert notifier.offer({'event': 'first'}) is True
        assert notifier.offer({'event': 'second'}) is False
        assert notifier.queue.qsize() == 1 and notifier.dropped == 1
    asyncio.run(scenario())


def test_t10_json_extra_field_rejected(tmp_path):
    app = vt.create_app(tmp_path/'audit.db')
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000'], 'send_to': 'anyone'})
    assert response.status_code == 422 and app.state.audit.rows() == []


def test_t11_primary_error_never_notifies(tmp_path):
    class UnknownStudent(vt.SyntheticRepo):
        def student_programs(self, uni, code):
            return __import__('pandas').DataFrame()
    events = []
    async def send(event):
        events.append(event)
    app = vt.create_app(tmp_path/'audit.db', sender=send, repo=UnknownStudent())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        drain(client, app)
    assert response.status_code == 404 and events == [] and app.state.audit.rows() == []


def test_t12_code32_unknown_partition_is_domain_result(tmp_path):
    app = vt.create_app(tmp_path/'audit.db')
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['X'*32]})
    assert response.status_code == 200
    assert response.json()['violations'][0]['code'] == 'not_in_curriculum'


def test_t13_order_shared_state_isolation(tmp_path):
    for index in range(2):
        app = vt.create_app(tmp_path/f'audit{index}.db')
        with TestClient(app) as client:
            response = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        assert response.status_code == 200
        assert [row[0] for row in app.state.audit.rows()] == [1]


def test_t14_saturation_keeps_all_commits(tmp_path):
    import threading
    started = threading.Event()
    release = asyncio.Event()
    async def send(event):
        started.set()
        await release.wait()
    app = vt.create_app(tmp_path/'audit.db', sender=send, queue_size=1, send_timeout=5)
    with TestClient(app) as client:
        first = client.post('/experiment/plan-check', json={'course_codes': ['C000']})
        assert started.wait(2), 'no sender started after committed main request'
        second = client.post('/experiment/plan-check', json={'course_codes': ['C001']})
        third = client.post('/experiment/plan-check', json={'course_codes': ['C002']})
        assert [first.status_code, second.status_code, third.status_code] == [200]*3
        assert len(app.state.audit.rows()) == 3 and app.state.notifier.dropped == 1
        client.portal.call(release.set)
        drain(client, app)


def test_t15_empty_code_rejected(tmp_path):
    app = vt.create_app(tmp_path/'audit.db')
    with TestClient(app) as client:
        response = client.post('/experiment/plan-check', json={'course_codes': ['']})
    assert response.status_code == 422 and app.state.audit.rows() == []
