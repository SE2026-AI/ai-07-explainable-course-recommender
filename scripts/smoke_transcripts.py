"""Gửi 4 bảng điểm mẫu ở test/fixtures/transcripts/ tới API đang chạy, in status và số gợi ý.

    python scripts/smoke_transcripts.py [--base http://127.0.0.1:8000/v1]

Thoát mã 1 nếu transcript không trả 200, hoặc recommendations trả lỗi khác 404 (404 = chưa có API-5, #51).
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "test" / "fixtures" / "transcripts"


def post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000/v1")
    base = parser.parse_args().base.rstrip("/")

    failed = False
    print(f"{'File':<28} {'transcript':>10} {'recommendations':>16} {'Số gợi ý':>9}")
    for path in sorted(FIXTURES.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        url = f"{base}/universities/{fx['university_code']}/curricula/{fx['curriculum_code']}"
        req = fx["request"]
        t_status, _ = post(f"{url}/transcript", {k: req[k] for k in ("semesters_completed", "results")})
        r_status, r_body = post(f"{url}/recommendations", req)
        if r_status == 200:
            count = str(len(r_body["items"]))
        elif r_status == 404:
            count = "chưa có API-5"
        else:
            count = "-"
        failed |= t_status != 200 or r_status not in (200, 404)
        print(f"{path.name:<28} {t_status:>10} {r_status:>16} {count:>9}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
