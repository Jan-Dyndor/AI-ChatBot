# AI Conversational Chatbot

A local chatbot with FastAPI, Streamlit, Ollama, and document search. Users can
create an account, chat, and upload PDFs for retrieval-augmented answers.

## Before you start

Install [Git](https://git-scm.com/downloads) and [Ollama](https://ollama.com/download).
The commands below use a POSIX shell (bash or zsh). Clone the repository:

```bash
git clone https://github.com/Jan-Dyndor/AI-ChatBot.git
cd AI-ChatBot
```

Open the Ollama desktop app, or run `ollama serve` in another terminal. On Linux
with Docker Engine, set `OLLAMA_HOST=0.0.0.0:11434` for the Ollama service and
restart it. If using the CLI, run `OLLAMA_HOST=0.0.0.0:11434 ollama serve`.
This lets containers reach Ollama; restrict port `11434` to trusted networks.
See the
[Ollama FAQ](https://github.com/ollama/ollama/blob/main/docs/faq.mdx).
With Ollama running, download both models:

```bash
ollama pull llama3:8b
ollama pull embeddinggemma
```

## Docker Compose (recommended)

Install and start [Docker Desktop](https://docs.docker.com/desktop/) or Docker
Engine with Compose on Linux. Compose runs Streamlit, FastAPI, Celery,
PostgreSQL, ChromaDB, Redis, and Flower. Ollama stays on your computer; see the
[architecture decision](docs/adr/0001-native-ollama-outside-docker-compose.md).

1. Copy the configuration template:

   ```bash
   cp .env.docker.example .env.docker
   ```

2. Edit `.env.docker` and replace every `CHANGE_ME` value. Use the same password
   in `POSTGRES_PASSWORD` and `DB_URL`; choose letters and digits unless you
   URL-encode special characters in `DB_URL`. Generate `SECRET_KEY` with
   `openssl rand -hex 32`.

3. Start the stack and create the database tables:

   ```bash
   docker compose up --build -d
   docker compose exec backend uv run alembic upgrade head
   ```

4. Open [http://localhost:8501](http://localhost:8501), select **Create new
   account**, then sign in. Select `llama3:8b` for chat; `embeddinggemma` is used
   to index and search PDFs. The [API health endpoint](http://localhost:8001/v1/)
   and [Flower](http://localhost:5555) are available separately.

For later starts use `docker compose up -d`. After pulling new migrations, run
`docker compose exec backend uv run alembic upgrade head` again. Stop with
`docker compose down`. Docker volumes retain data; `docker compose down -v`
**deletes the database, uploads, vectors, and Redis data**.

If startup fails, check `docker compose ps`,
`docker compose logs backend celery_worker`, and `ollama list`.
Containers reach Ollama at
`host.docker.internal:11434`; their own `localhost` is different. Make sure
ports `8000`, `8001`, `8501`, `5433`, `6379`, and `5555` are free.

## Run without Docker

These commands use macOS and [Homebrew](https://brew.sh/) for PostgreSQL and
Redis. On another operating system, install and start PostgreSQL 18 and Redis 8
with your package manager. You also need
[uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Rust](https://rust-lang.org/install) (`cargo` and `rustc`). Use the repository
cloned above and run commands from its root unless a command changes directory.

1. Start PostgreSQL and Redis, then create the application database.
   `createuser` asks for a password; use it in `.env` below.

   ```bash
   brew install postgresql@18 redis
   export PATH="$(brew --prefix postgresql@18)/bin:$PATH"
   brew services start postgresql@18
   brew services start redis
   createuser --pwprompt ai_chatbot
   createdb --owner=ai_chatbot ai_chatbot
   ```

2. In the same terminal (with PostgreSQL on `PATH` for `pg_config`), install
   Python 3.14 and the project dependencies, including its Rust extension:

   ```bash
   uv python install 3.14
   uv sync --locked
   (
     export VIRTUAL_ENV="$PWD/.venv"
     cd src/backend/rust_sha256
     "$VIRTUAL_ENV/bin/maturin" develop --release
   )
   uv run python -c "import rust_sha256"
   cp .env.example .env
   ```

   In `.env`, replace all `CHANGE_ME` values and generate `SECRET_KEY` with
   `openssl rand -hex 32`. Set `DB_URL` to
   `postgresql://ai_chatbot:YOUR_PASSWORD@localhost:5432/ai_chatbot`. Keep the
   ChromaDB and Redis settings as provided. Use a URL-safe database password or
   URL-encode special characters.

3. Run Chroma in one terminal, then apply the database migrations in another:

   ```bash
   uv run chroma run --path ./chroma-data --host localhost --port 8000
   ```

   ```bash
   uv run alembic upgrade head
   ```

4. Start these processes in separate terminals:

   ```bash
   uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001 --no-access-log
   ```

   ```bash
   uv run streamlit run src/frontend/main.py
   ```

   ```bash
   uv run celery -A backend.celery_app.celery_app:celery_app worker --loglevel=INFO --pool=solo
   ```

Open [http://localhost:8501](http://localhost:8501) and create an account.
The Celery worker indexes uploaded PDFs. Stop application processes with
`Ctrl+C`; on macOS, stop PostgreSQL and Redis with
`brew services stop postgresql@18` and `brew services stop redis`. Run
`uv run alembic upgrade head` after pulling new migrations.

## Configuration and services

| Service | Docker Compose | Local |
| --- | --- | --- |
| Streamlit | `localhost:8501` | `localhost:8501` |
| FastAPI | `localhost:8001` | `localhost:8001` |
| ChromaDB | `localhost:8000` | `localhost:8000` |
| PostgreSQL | `localhost:5433` | `localhost:5432` |
| Redis | `localhost:6379` | `localhost:6379` |
| Ollama | host `localhost:11434` | `localhost:11434` |

`.env.docker` uses Compose service names (`backend`, `postgres`, `chroma`);
`.env` uses `localhost`. Neither file should be committed. The examples use
`llama3:8b` for chat and `embeddinggemma` for PDFs. You can download and select
another chat model; `EMBEDDING_MODEL` must match an installed embedding model.
LangSmith tracing is optional and disabled in both templates.

## Current Features

- Account registration and JWT login; multiple conversations with saved history.
- Ollama model selection, generation settings, and streamed chat responses.
- History-aware RAG over PDFs, with retrieval limited to the current user.
- PDF upload (10 MB default), background indexing, status, preview, and deletion.
- Redis conversation locks and request ID logging; optional LangSmith tracing.

## Project Structure

[Architecture diagram](https://mermaid.ai/d/210c41c3-156e-4bde-9dbb-ae3b78509538)

```text
AI-ChatBot/
├── src/backend/          FastAPI, auth, services, Celery, database, Rust extension
├── src/frontend/         Streamlit UI and pages
├── src/RAG/              PDF indexing and ChromaDB integration
├── alembic/              PostgreSQL migrations
├── tests/                API, service, and RAG evaluation tests
├── docs/                 Architecture decisions and file deletion lifecycle
├── storage/              Local PDF uploads; Docker uses a named volume
├── compose.yaml          Container services and volumes
├── .env*.example         Configuration templates
└── pyproject.toml        Python dependencies (locked in uv.lock)
```

PostgreSQL stores accounts and chat history. Celery indexes uploaded PDFs in
ChromaDB with Ollama embeddings; Redis carries tasks and conversation locks.
See [file deletion](docs/file-deletion.md) and the
[architecture decisions](docs/adr/README.md) for details.

## RAG evaluations

The optional DeepEval scripts use the benchmark PDF in `tests/RAG_evals/data/`
and a temporary local Chroma collection. They need installed Python dependencies,
a configured `.env`, and Ollama with both models; no separate Chroma server or
PostgreSQL is needed. Run one script at a time:

```bash
uv run python tests/RAG_evals/single_turn_test.py
# or
uv run python tests/RAG_evals/multi_turn_rag_test.py
```

Reports go to `evals_results/`. To evaluate another PDF, update the benchmark
file and matching golden JSON in `tests/RAG_evals/`.
