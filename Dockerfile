FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini LICENSE THIRD_PARTY_NOTICES.md ./
COPY LICENSES ./LICENSES
COPY aac_backend ./aac_backend
COPY web ./web

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn aac_backend.main:app --host 0.0.0.0 --port 8000"]
