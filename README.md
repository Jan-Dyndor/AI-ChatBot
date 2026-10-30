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

## Run the application

The FastAPI backend uses port `8001`, ChromaDB uses `8000`, and the Streamlit
frontend uses `8501`. Ollama runs on the host at `11434` and needs the chat and
embedding models before either setup can be used. Start Docker Desktop and make
sure Ollama is running, then download the models:

```bash
ollama pull llama3:8b
ollama pull embeddinggemma
```

### 1. Run everything with Docker Compose

Use this option when you want the complete application stack in containers.
Copy [`.env.docker.example`](.env.docker.example) to `.env.docker` and replace
every `CHANGE_ME` value. The template already uses the Compose service names
for the backend, PostgreSQL, and ChromaDB. Use the same password in
`POSTGRES_PASSWORD` and `DB_URL`.

```bash
cp .env.docker.example .env.docker
docker compose up --build -d

# First run, and again after pulling a migration.
docker compose exec backend uv run alembic upgrade head
```

Open `http://localhost:8501`. Docker Compose starts the frontend, backend,
PostgreSQL, and ChromaDB.

For later starts, run `docker compose up -d`. Use `docker compose down` to stop
the stack. The `postgres_data`, `uploaded_files`, and `chroma_data` volumes
keep their data unless you use `docker compose down -v`.

### 2. Debug FastAPI and Streamlit locally

Use this option when you want automatic reload and debugger access for the
Python applications while PostgreSQL and ChromaDB remain in Docker.

Create both environment files. `.env.docker` configures the Docker services;
`.env` configures the local FastAPI and Streamlit processes. Set the same
PostgreSQL password in `.env.docker` and in the `DB_URL` value in `.env`.

```bash
cp .env.docker.example .env.docker
cp .env.example .env
```

Start only the supporting services, then create the database schema:

```bash
docker compose up -d postgres chroma
uv run alembic upgrade head
```

Run the application processes from the repository root in separate terminals:

```bash
# Terminal 1 — FastAPI with automatic reload
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001 --no-access-log
```

```bash
# Terminal 2 — Streamlit
uv run streamlit run src/frontend/main.py
```

Open `http://localhost:8501`. In this mode, [`.env.example`](.env.example)
points the local applications to FastAPI at `localhost:8001`, ChromaDB at
`localhost:8000`, and PostgreSQL at `localhost:5433`.

Run `uv run alembic upgrade head` on the first start and whenever the project
contains a new database migration. Stop the supporting services with
`docker compose down`.

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
├── compose.yaml                 # Frontend, backend, PostgreSQL, and ChromaDB services
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
4. The ChromaDB service persists the embeddings in the `chroma_data` Docker
   volume.
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
