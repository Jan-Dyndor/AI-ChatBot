FROM python:3.14-slim

# To install psycopg2 
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl\
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install rust compiler
RUN curl -fsSLo /tmp/rustup-init.sh https://sh.rustup.rs \
    && sh /tmp/rustup-init.sh -y \
    && rm /tmp/rustup-init.sh

ENV PATH="/root/.cargo/bin:${PATH}"

RUN rustc --version && cargo --version


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR /app_backend

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/backend ./src/backend
COPY src/RAG ./src/RAG
COPY alembic  ./alembic 
COPY alembic.ini ./


RUN uv sync --locked --no-dev

ENV VIRTUAL_ENV=/app_backend/.venv
WORKDIR /app_backend/src/backend/rust_sha256
RUN /app_backend/.venv/bin/maturin develop --release

WORKDIR /app_backend
EXPOSE 8001

CMD ["uv", "run", "--no-dev", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]