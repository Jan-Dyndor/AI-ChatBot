# AI Conversational Chatbot

Local AI conversational chatbot with contextualized RAG, built with FastAPI, Streamlit, LangChain and Ollama.

The goal of this project is to understand how production-oriented LLM applications work, from streaming responses and conversation history to authentication, persistence and observability.

The project started with direct LLM integration to explore the underlying mechanics. It now uses LangChain for LLM interactions and retrieval while keeping application architecture, conversation management and backend services explicit.

## Project Goals

This project was created to explore and understand:

- LLM application architecture
- streaming AI responses
- backend/frontend separation
- conversational memory handling
- authentication & session management
- observability and monitoring
- async Python backend systems
- understanding the trade-offs between direct integrations and framework abstractions
- document ingestion, embeddings and vector similarity search
- contextualized retrieval using conversation history

## Architecture decisions

Important technical decisions are recorded as Architecture Decision Records
(ADRs). Start with the [ADR index](docs/adr/README.md).

- [ADR 0001: Run Ollama natively instead of in Docker Compose](docs/adr/0001-native-ollama-outside-docker-compose.md)

## Running with Docker Compose

Docker Compose runs three parts of the application: the Streamlit frontend,
the FastAPI backend, and PostgreSQL. Ollama is intentionally **not** a Compose
container: it runs natively on the user's computer. The reasoning behind this
decision is documented in [ADR 0001](docs/adr/0001-native-ollama-outside-docker-compose.md).

```text
Browser -> frontend:8501 -> backend:8000 -> PostgreSQL
                                  |
                                  +-> Ollama on the host:11434
```

A Dockerfile is a recipe for an image, an image is a packaged version of the
application, and a container is a running instance of an image.
`docker compose up --build` builds images, creates the network and volumes, and
then starts the containers defined in `compose.yaml`.

### Requirements

1. Docker Desktop must be running.
2. Ollama must be installed natively on the same computer as Docker.
3. The Ollama service must listen on its default port, `11434`.
4. Download both required models (or choose  embedding one since llama3:8b is required in DeepEval tests). You can download more models and use them as you like :

   ```bash
   ollama pull llama3:8b
   ollama pull embeddinggemma
   ollama list
   ```

   `llama3:8b` is the default conversation model. The application uses it for
   responses, conversation summaries, and conversation titles; users can later
   select another downloaded model. `embeddinggemma` is the example embedding model:
   it indexes PDFs and retrieves RAG context. An embedding model cannot generate
   chat responses. You may use another Ollama embedding model, but it must be
   installed and its name must exactly match `EMBEDDING_MODEL` in env files.

   The Ollama macOS app normally starts its server automatically. If
   `curl http://localhost:11434/api/tags` does not return a response, run:

   ```bash
   ollama serve
   ```

### `.env.docker` configuration

Do not share or commit a real `.env.docker`: it contains the database password
and JWT secret. Git ignores this file. The safe, versioned template is
[`.env.docker.example`](.env.docker.example).

Create your private file and replace every `CHANGE_ME` value:

```bash
cp .env.docker.example .env.docker
```

`backend` and `postgres` are Docker Compose service names. Inside the Compose
network, `localhost` means the current container, so the frontend cannot reach
the backend at `http://localhost:8000`.

`OLLAMA_API=http://host.docker.internal:11434` has a different role: it routes
from the backend container to the Ollama service running on the host computer.
This is the correct value for Docker Desktop on macOS and Windows.

`API_CONVERSATIONS_BY_ID_PART` must end with a slash. The code constructs the
conversation-history URL by concatenation:

```text
http://backend:8000/v1/conversations/ + 42 + /messages
= http://backend:8000/v1/conversations/42/messages
```

The legacy endpoint variables (`API_CHAT_HISTORY_URL`,
`API_CREATE_CONVERSATION_URL`, and `API_LATEST_CONVERSATIONS_IDS_URL`) remain
in the file because the current `Settings` object validates them as required.
They are safe API URLs, although the current frontend uses the newer
`API_CONVERSATIONS*` variables.

`LANGSMITH_*` is required by the configuration, but LangSmith is functionally
optional: with `LANGSMITH_TRACING=false`, its API key may remain empty.
`TEST_DEEPEVALS_*` is only used when manually running RAG evaluations, not in
normal application use.

`EMBEDDING_MODEL` is the model used to create vectors for document indexing and
RAG retrieval. It can name any embedding-capable model installed in Ollama. For
example, if you use `embeddinggemma`, both commands must agree:

```bash
ollama pull embeddinggemma
```

```env
EMBEDDING_MODEL=embeddinggemma
```

If you change the embedding model after documents have already been indexed,
rebuild the Chroma collection and reindex the documents. Vectors produced by
different embedding models should not share one collection.

For local deployment simplicity, the same environment file is currently passed
to both the frontend and backend. A production deployment should separate
service-specific variables and not pass database credentials to the frontend
container.

### First startup

From the repository root, run these commands in order:

```bash
# 1. Build the images and start the frontend, backend, and PostgreSQL in the background.
docker compose -p ai-chatbot up --build -d

# 2. Check that the services are running.
docker compose -p ai-chatbot ps
docker compose -p ai-chatbot logs --tail=100 backend

# 3. Create or update the PostgreSQL tables.
docker compose -p ai-chatbot exec backend uv run alembic upgrade head

# 4. Check the backend health endpoint.
curl http://localhost:8000/v1/
```

The Alembic migration is intentionally a separate step. The PostgreSQL
container creates an empty database, but it does not know about the
application's SQLAlchemy models; `alembic upgrade head` creates its tables.
Run this command on first startup and after pulling a version that contains a
new migration. Then open the frontend at `http://localhost:8501`.

For later starts with no code changes, use:

```bash
docker compose -p ai-chatbot up -d
```

After changing code, dependencies, a Dockerfile, or image configuration, use:

```bash
docker compose -p ai-chatbot up --build -d
```

Stopping the application does not remove data:

```bash
docker compose -p ai-chatbot down
```

The `postgres_data`, `uploaded_files`, and `chroma_db` volumes persist the
database, uploaded files, and vector index respectively. Do not use `down -v`
when you want to preserve them: that option removes the volumes and their data.

### What can be shared safely

[`.env.example`](.env.example) is the public template for running without
Docker: its endpoints point to `localhost` and `OLLAMA_API` is
`http://localhost:11434`. [`.env.docker.example`](.env.docker.example) is the
public Compose template and uses the `backend` and `postgres` service names.

The repository can contain endpoint URLs, model names, limits, and blank or
descriptive placeholders. Never add real values for `SECRET_KEY`,
`POSTGRES_PASSWORD`, a complete production `DB_URL`, or `LANGSMITH_API_KEY`.
Those values belong only in ignored `.env` or `.env.docker` files, or in a
secret manager on the target infrastructure.

## Running without Docker (local development)

Copy [`.env.example`](.env.example) to `.env`, configure a local PostgreSQL
database, start Ollama, and apply the migration:

```bash
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log
uv run streamlit run src/frontend/main.py
```

To process more parallel requests, start Ollama with
`OLLAMA_NUM_PARALLEL=<number> ollama serve`. A larger value increases the RAM
used by loaded models.

## DeepEval RAG evaluations

The repository contains two standalone DeepEval scripts. They run the real RAG
pipeline against a local benchmark PDF and Ollama; they are excluded from the
default `pytest` run.

- `tests/RAG_evals/single_turn_test.py` — evaluates independent, single-turn RAG questions.
- `tests/RAG_evals/multi_turn_rag_test.py` — evaluates conversations containing multiple related turns.

Start Ollama and download the default chat and embedding models:

```bash
ollama pull llama3:8b
ollama pull embeddinggemma
```

Set the model configuration in the repository-root `.env` file:

```env
EMBEDDING_MODEL="embeddinggemma"
TEST_DEEPEVALS_MODEL="llama3:8b"
TEST_DEEPEVALS_TEMP=0
TEST_DEEPEVALS_TOP_K=40
TEST_DEEPEVALS_TOP_P=0.9
TEST_DEEPEVALS_NUM_CTX=4096
TEST_DEEPEVALS_NUM_PREDICT=300
TEST_DEEPEVALS_REPEAT_PENALTY=1.1
TEST_DEEPEVALS_IS_THINKING=false
```

Run one script at a time from the repository root:

```bash
uv run python tests/RAG_evals/single_turn_test.py
# or
uv run python tests/RAG_evals/multi_turn_rag_test.py
```

### How it works

Each script loads the benchmark PDF from `tests/RAG_evals/data/`, splits it into
chunks, creates embeddings, and puts them in a temporary Chroma collection. It
then reads the matching golden file (`single_turn_goldens.json` or
`multi_turn_goldens.json`), asks the RAG chain each question, and compares its
answer and retrieved context with the expected result.

The test document and all searches use the isolated `user_id = -1`, so only its
chunks can be retrieved. This mirrors the application's user-level document
filtering without requiring a backend server, database, account, or file upload.
The temporary vectors are deleted after the script ends.

To test another document, replace the PDF at
`tests/RAG_evals/data/harborline_rag_benchmark_10_pages.pdf` (or update
`test_docs_path` in both scripts) and update the corresponding golden JSON with
questions and expected answers. Use the single-turn golden file for independent
questions; use the multi-turn file for follow-up questions that depend on chat
history.

The single-turn evaluation currently measures contextual relevancy. The
multi-turn evaluation measures faithfulness plus contextual relevancy,
precision, and recall. Results are saved as HTML reports under
`evals_results/single/basic/test_results/` or
`evals_results/multi/basic/test_results/`; each run also overwrites its saved
configuration and an example of the generated chunks in `evals_results/`.

If DeepEval reports a timeout, increase its per-attempt and per-task timeouts before running the command again:

```bash
export DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE=600
export DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE=600

uv run python tests/RAG_evals/single_turn_test.py
# or
uv run python tests/RAG_evals/multi_turn_rag_test.py
```

The value `600` is only a starting point. Adjust it to match the available hardware, the selected model, and whether the evaluation is running asynchronously.

## Architecture

Frontend:
- Streamlit

Backend API:
- FastAPI

LLM Integration:
- LangChain
- ChatOllama for communication with local Ollama models

Retrieval-Augmented Generation:
- LangChain history-aware retriever
- Chroma persistent vector store
- Ollama embeddings
- PDF loading and recursive text splitting

Persistence:
- PostgreSQL 

Caching (planned):
- Redis

Validation:
- Pydantic v2

Logging:
- Loguru

Infrastructure (planned):
- Docker & Docker Compose

Monitoring (planned):
- Grafana + Loki + Prometheus

## Project Structure

```text
AI-ChatBot/
├── .github/
│   └── workflows/              # GitHub Actions workflows
│
├── src/
│   ├── RAG/
│   │   ├── chroma_db.py                    # Persistent Chroma vector-store setup
│   │   ├── document_indexing_seervice.py   # PDF loading and text chunking
│   │   └── file_vector_repository.py       # Document indexing and retrieval adapter
│   │
│   ├── backend/
│   │   ├── api/                # FastAPI routers and API endpoints and Pydantic schemas
│   │   ├── authentication/     # Authentication, password hashing and JWT handling
│   │   ├── chat_bot/           # LLM/Ollama communication logic
│   │   ├── configuration/      # Settings and logging configuration
│   │   ├── core/               # Utils files. Threading Lock
│   │   ├── database/           # SQLAlchemy models, engine and DB setup, repository class setup
│   │   ├── dependencies/       # FastAPI dependencies
│   │   ├── exceptions/         # Custom exceptions and handlers
│   │   ├── middleware/         # Request ID and logging middleware
│   │   ├── service/            # Business logic and orchestration layer
│   │   └── main.py             # FastAPI application entrypoint
│   │
│   └── frontend/
│       ├── main.py             # Streamlit application entrypoint
│       └── pages/
│           ├── chatbot_page.py # Chat UI
│           ├── login_page.py   # Login UI
│           ├── register_page.py # Registration UI
│           ├── upload_page.py  # PDF upload UI
│           └── files_page.py   # User document list UI
│
├── tests/                      # Unit and integration tests
├── alembic/                     # Database migration environment and revisions
├── storage/                     # Uploaded files, organized by user at runtime
├── vector_storage/              # Persistent Chroma data at runtime
├── .gitignore
├── .env                        # Env file with env variables
├── .env.tests                  # Env file with env variables for tests purposes 
├── .env.example                # Example env file with env variables that application needs
├── .python-version
├── README.md
├── pyproject.toml              # Project configuration and dependencies
└── uv.lock                     # Locked dependency versions
```

## Contextualized RAG

Authenticated users can upload PDF documents from the Streamlit upload page. The backend stores the file and its metadata, then indexes the PDF in a background task:

1. `PyPDFLoader` loads the PDF.
2. `RecursiveCharacterTextSplitter` creates chunks using the configured `chunk_size` and `chunk_overlap` settings.
3. `OllamaEmbeddings` creates embeddings for each chunk.
4. Chroma persists the embeddings in `vector_storage/`.
5. Each chunk receives the owning `user_id` as metadata.

When a user sends a chat message, the RAG pipeline uses the conversation history to rewrite follow-up questions into standalone questions. A history-aware LangChain retriever then searches the user's documents only (`k=3`), and the retrieved context is passed to the Ollama chat model to generate a streamed answer. The completed answer is saved to the conversation history.

The upload endpoint is `POST /v1/file`, and the RAG chat endpoint is `POST /v1/chat`. PDF uploads are limited by `MAX_FILE_SIZE_BYTES` (10 MB by default).

## Streaming Responses

The backend streams responses from Ollama through FastAPI StreamingResponse.

The Streamlit frontend consumes streamed chunks in real-time to simulate ChatGPT-like interaction.

## Concurrency and Conversation Locking

The backend uses an in-memory `threading.Lock` for each conversation.

Requests targeting the same conversation are processed sequentially. This
prevents concurrent requests from modifying the conversation history while
an assistant response is still being generated and streamed.

Different conversations use separate locks and can be processed concurrently.
However, actual parallel LLM generation also depends on the Ollama
`OLLAMA_NUM_PARALLEL` configuration.

### Current limitation

The lock manager stores its locks in the memory of a single Python process.
Therefore, the current implementation is safe only when FastAPI runs with
one Uvicorn worker.

Multiple Uvicorn workers would maintain separate lock registries, so requests
handled by different workers would not share the same conversation locks.

A distributed lock, for example using Redis, will be required before running
the application with multiple workers or multiple backend instances.

## Current Features

- LangChain integration for LLM interactions and prompt construction
- Streaming AI responses
- FastAPI backend API
- Streamlit frontend UI
- Chat history 
- Request tracing middleware
- Structured logging with Loguru
- Pydantic settings & validation
- Project managed with uv
- Installed as editable Python package
- Basic test suite
- Layered backend architecture
- Persistent chat history (PostgreSQL; SQLite for tests)
- Multi-chat support 
- Multiple LLM models supported through Ollama
- JWT-based authentication
- CI with GitHub Actions
- Per-conversation request locking within a single FastAPI process
- PostgreSQL integration
- Continuous Integration with GitHub Actions
- Contextualized RAG over user-uploaded PDF documents
- Persistent Chroma vector store with Ollama embeddings
- User-scoped document retrieval
- PDF upload page in the Streamlit frontend


## Planned Features
- Redis-based conversational memory
- Voice input (speech-to-text)
- AI text-to-speech responses
- User metrics dashboard
- Grafana/Loki and Prometheus observability stack
- CD with GitHub Actions
- Dockerized deployment
- Redis-based distributed conversation locking for multi-worker deployment


## LangChain Integration

The initial implementation used direct Ollama integration to build an understanding of prompt handling, streaming, conversation management and error handling.

The project now uses LangChain for model interaction, prompt construction and contextualized retrieval. Authentication, persistence, conversation locking, file management and application-level orchestration remain part of the project's own backend services.

The learning goal remains the same: understand how each component works, why an abstraction is useful and which responsibilities belong to the application.
The main goal is to understand:
- streaming mechanics
- prompt handling
- memory management
- contextualized retrieval and document grounding
- API communication
- retries & error handling
- observability
- architecture decisions


## Learning Focus

This project is primarily focused on learning how modern AI systems are built in practice.

The emphasis is on:
- backend engineering
- system architecture
- AI infrastructure
- observability
- streaming systems
- production-oriented thinking
