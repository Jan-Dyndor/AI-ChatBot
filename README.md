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

## How to run (Docker planned later on)
Make sure Ollama is installed and pull both a chat model and an embedding model. The chat model generates answers; the embedding model is required to index and search uploaded PDFs.

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

Create a `.env` file in the root of the repository for local development. Use `.env.example` as a template for the required variables.

Set `EMBEDDING_MODEL` to the embedding model you pulled. For the commands above:

```env
EMBEDDING_MODEL="nomic-embed-text"
```

`EMBEDDING_MODEL` must reference an Ollama model that supports embeddings. If it is empty or points to a model that cannot generate embeddings, PDF indexing will fail when an uploaded document is processed.

Example `.env`:

```env
# PostgreSQL database URL used for local development.
DB_URL="postgresql://user:password@localhost:5432/database_name"
```

If you want to run tests locally, create a separate `.env.tests` file with test-only values.

Example `.env.tests`:

```env
# In-memory SQLite database used for tests.
DB_URL="sqlite:///:memory:"
```

Before starting the backend:

1. Make sure PostgreSQL is running.
2. Create the PostgreSQL database specified in `DB_URL`.
3. From the repository root, apply all database migrations:

```bash
uv run alembic upgrade head
```

Run this command during the initial setup and whenever new database migrations are added.


The application uses Pydantic Settings to load environment variables from the `.env`s files.

Follow the command from root of the repo

### Ollama
If you want to run multiple queires at once you have to run Ollama with below command in command line:
```cmd
OLLAMA_NUM_PARALLEL= number ollama serve
```
Where number is a maximum number of parallel requests each model will process at the same time, default 1. Required RAM will scale by OLLAMA_NUM_PARALLEL

### Backend
```cmd
uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log
```

### Frontend
```cmd
 uv run streamlit run src/frontend/main.py
```

## DeepEval RAG evaluations

The repository contains two DeepEval RAG evaluation scripts:

- `tests/RAG_evals/single_turn_test.py` — evaluates independent, single-turn RAG questions.
- `tests/RAG_evals/multi_turn_rag_test.py` — evaluates conversations containing multiple related turns.

Run the evaluations from the repository root with `uv`:

```bash
uv run python tests/RAG_evals/single_turn_test.py
uv run python tests/RAG_evals/multi_turn_rag_test.py
```

The evaluations use the local Ollama model configured in the scripts (`llama3:8b`) and may take a while to finish. If DeepEval reports a timeout, increase its per-attempt and per-task timeouts before running the command again:

```bash
export DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE=600
export DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE=600

uv run python tests/RAG_evals/single_turn_test.py
# or
uv run python tests/RAG_evals/multi_turn_rag_test.py
```

The value `600` is only a starting point. Adjust it to match the available hardware, the selected model, and whether the evaluation is running asynchronously.

### Preparing documents for RAG evaluation

The RAG evaluation scripts retrieve context from the vector store, so the source document used by the goldens must be uploaded and indexed before running an evaluation. Upload the document through the `POST /v1/file` endpoint defined in `src/backend/api/router/v1.py`. The endpoint saves the file, splits it into chunks, and creates embeddings for those chunks.

For repeatable evaluation runs, create a dedicated test account, upload the evaluation document while authenticated as that user, and save the user ID returned by the application. Then change the `user_id` argument in both evaluation scripts from the example value:

```python
rag_chain = service.build_rag_chain(
    model="llama3:8b",
    temperature=0,
    top_k=40,
    top_p=0.9,
    num_ctx=4096,
    num_predict=300,
    repeat_penalty=1.1,
    is_thinking=False,
    user_id=1,
)
```

to the ID of the dedicated test user, for example `user_id=42`.

This is important because retrieval is scoped by `user_id`: the RAG chain must return only documents and chunks belonging to the test user. If the document is uploaded under a different account, or the script uses the wrong ID, the evaluation may retrieve no context or context from the wrong user's documents.

In the future, I will improve the functionality or rethink this approach to make preparing and running the evaluations easier.

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
│           └── upload_page.py  # PDF upload UI
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
