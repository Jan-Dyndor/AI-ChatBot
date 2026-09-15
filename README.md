# AI Conversational Chatbot

Local AI conversational chatbot built with FastAPI, Streamlit and Ollama.

The goal of this project is to deeply understand how production-oriented LLM systems work under the hood without relying on high-level AI orchestration frameworks such as LangChain.

## Project Goals

This project was created to explore and understand:

- LLM application architecture
- streaming AI responses
- backend/frontend separation
- conversational memory handling
- authentication & session management
- observability and monitoring
- async Python backend systems
- AI system design without abstraction-heavy frameworks

## How to run (Docker planned later on)
Make sure you have the default Ollama model downloaded:

```bash
ollama pull llama3:8b
```

Create a `.env` file in the root of the repository for local development. Use `.env.example` as a template for the required variables.

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
## Architecture

Frontend:
- Streamlit

Backend API:
- FastAPI

LLM Runtime:
- Ollama (local models)

Persistence (planned):
- PostgreSQL (SQLite in tests)

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
│   ├── backend/
│   │   ├── api/                # FastAPI routers and API endpoints and Pydantic schemas
│   │   ├── authorization/      # Auth service class responsible for authorization and JWT creation
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
│       └── main.py             # Entry point of Streamlit applications 
│       ├── pages/              # Streamlit frontend pages
│           └── chatbot_page.py 
│           └── login_page.py 
│           └── register_page.py            
│
├── tests/                      # Unit and integration tests
├── .gitignore
├── .env                        # Env file with env variables
├── .env.tests                  # Env file with env variables for tests purposes 
├── .env.example                # Example env file with env variables that application needs
├── .python-version
├── README.md
├── pyproject.toml              # Project configuration and dependencies
└── uv.lock                     # Locked dependency versions
```

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

- Local LLM chatbot using Ollama
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
- Persistent chat history (SQLite)
- Multi-chat support 
- Mulit-LLMs support 
- JWT/O2Auth authentication
- CI with GitHub Actions
- Per-conversation request locking within a single FastAPI process
- PostgreSQL integration


## Planned Features
- Redis-based conversational memory
- Voice input (speech-to-text)
- AI text-to-speech responses
- User metrics dashboard
- Grafana/Loki and Prometheus observability stack
- CI/CD with GitHub Actions
- Dockerized deployment
- RAG support
- Redis-based distributed conversation locking for multi-worker deployment


## Why No LangChain?

This project intentionally avoids high-level LLM orchestration frameworks.

The main goal is to understand:
- streaming mechanics
- prompt handling
- memory management
- API communication
- retries & error handling
- observability
- architecture decisions

before introducing abstraction layers.

## Learning Focus

This project is primarily focused on learning how modern AI systems are built in practice.

The emphasis is on:
- backend engineering
- system architecture
- AI infrastructure
- observability
- streaming systems
- production-oriented thinking