# Tools

Place developer utilities, data scripts, and maintenance helpers here. Include setup and usage notes for every tool, and never store secrets.

## generate_synthetic_data.py (T-02)

Sinh dữ liệu giả lập tất định: cùng seed thì cho cùng output. Chỉ dùng thư viện chuẩn của Python 3.12+.

```bash
python tools/generate_synthetic_data.py --seed 42 --profiles 300 --out tools/out
```

| File | Nội dung |
|---|---|
| `catalog.json` | 24 môn học; 6 môn đầu khớp `docs/tasks/prompts/fixtures/reference-scenarios.json` |
| `goals.json` | Ánh xạ mục tiêu nghề nghiệp → skill tag |
| `profiles.json` | Hồ sơ hợp lệ theo schema `Profile` trong `docs/architecture/contracts/openapi.yaml` |
| `cohorts.json` | Nhãn nhóm `gender`/`region`/`academic_pattern`, **chỉ** dùng cho fairness checks, không bao giờ gửi lên API |

`tools/out/` nằm trong `.gitignore`, nên chạy lại tool khi cần dữ liệu. Test: `python -m pytest test/backend/test_synthetic_data.py`.

## Planned

- `fairness_report.py` (T-13): tính F-03, F-04, F-06 trong `docs/architecture/FAIRNESS.md`.
- `ml_baseline.py` (T-14): baseline ML để lấy số liệu cho ADR-001.
