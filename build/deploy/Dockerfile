# Image chạy API AI-07. Build từ thư mục gốc của repo:
#   docker build -f build/deploy/Dockerfile -t ai07-api .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài thư viện trước, copy mã nguồn sau: đổi mã nguồn không phải cài lại thư viện.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY tools/ ./tools/
COPY data/ ./data/
COPY pytest.ini ./

# Không chạy bằng root.
RUN useradd --create-home --shell /usr/sbin/nologin app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
