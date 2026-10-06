# ai-07-explainable-course-recommender
SE2026-T24 (SE.2026.14) — AI-07 Explainable Course Recommender; API-first course recommendations with clear explanations for partner Web and Mobile integrations.

## Chạy MVP

Yêu cầu Python 3.12+.

```bash
pip install -e ".[dev]"
python -m pytest                                   # 72 test: tiên quyết, ranking, giải thích, what-if
uvicorn --app-dir src backend.app:app --reload     # API tại http://localhost:8000/v1/docs
```

Giao diện web (terminal thứ hai, cần Node 20+):

```bash
cd src/web && npm install
npm run dev        # http://localhost:5173 (gọi /v1 qua proxy tới :8000)
npm test           # test giao diện trong test/web
```

Muốn thử các trạng thái lỗi (degraded/503) trên giao diện thì chạy backend với `AI07_ALLOW_FAULTS=1`.

Tài liệu: [kiến trúc](docs/architecture/ARCHITECTURE.md) · [ADR rules vs ML](docs/architecture/adr/ADR-001-rules-vs-ml.md) · [fairness](docs/architecture/FAIRNESS.md) · [backlog](docs/tasks/BACKLOG.md).
Dữ liệu hoàn toàn là dữ liệu giả lập; điểm là mức phù hợp theo quy tắc, không phải xác suất thành công.
