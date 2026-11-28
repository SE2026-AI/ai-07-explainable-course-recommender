"""Gửi 4 bảng điểm mẫu ở test/fixtures/transcripts/ tới API đang chạy, in status và số gợi ý.

    python scripts/smoke_transcripts.py [--base http://127.0.0.1:8000/v1]

Thoát mã 1 nếu một endpoint không trả 200 hoặc phản hồi không đúng dạng. API-5 đã có trên main.
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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return 0, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000/v1")
    base = parser.parse_args().base.rstrip("/")

    failed = False
    fixtures = sorted(FIXTURES.glob("*.json"))
    if not fixtures:
        print("Không tìm thấy bảng điểm mẫu.", file=sys.stderr)
        return 1
    print(f"{'File':<28} {'transcript':>10} {'recommendations':>16} {'Số gợi ý':>9}")
    for path in fixtures:
        fx = json.loads(path.read_text(encoding="utf-8"))
        url = f"{base}/universities/{fx['university_code']}/curricula/{fx['curriculum_code']}"
        req = fx["request"]
        t_status, t_body = post(f"{url}/transcript", {k: req[k] for k in ("semesters_completed", "results")})
        r_status, r_body = post(f"{url}/recommendations", req)
        if r_status == 200 and isinstance(r_body, dict) and isinstance(r_body.get("items"), list):
            count = str(len(r_body["items"]))
        else:
            count = "-"
        failed |= t_status != 200 or not isinstance(t_body, dict) or r_status != 200 or count == "-"
        print(f"{path.name:<28} {t_status:>10} {r_status:>16} {count:>9}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
