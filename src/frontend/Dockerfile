FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# To install psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc

WORKDIR /app_frontend

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/frontend ./src/frontend
COPY src/backend ./src/backend
RUN uv sync --locked --no-dev

EXPOSE 8501

CMD ["uv", "run", "streamlit" , "run" ,"src/frontend/main.py"]