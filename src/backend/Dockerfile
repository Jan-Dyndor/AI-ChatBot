FROM python:3.14-slim

# To install psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR /app_backend

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/backend ./src/backend
COPY src/RAG ./src/RAG
COPY alembic  ./alembic 
COPY alembic.ini ./


RUN uv sync --locked --no-dev

EXPOSE 8001

CMD ["uv", "run", "--no-dev", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]