FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.110" \
    "uvicorn[standard]>=0.27" \
    "asyncpg>=0.29" \
    "pydantic>=2.6"

COPY app ./app

ENV PYTHONUNBUFFERED=1
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
