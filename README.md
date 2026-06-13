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
Create a `.env` file in the root of the repository and define:

```env
API_URL="http://localhost:8000/v1/chat"
API_CHAT_HISTORY="http://localhost:8000/v1/chat_history"
API_CREATE_CONVERSATION="http://localhost:8000/v1/create_conversation"
API_LATEST_CONVERSATIONS_IDS="http://localhost:8000/v1/get_conversations_ids"
SECRET_KEY = "SOME VALUE"
ALGORITHM = "HS256"


# Example SQLite database URL.
# You can change this path if you want to store the database elsewhere.
DB_URL="sqlite:///data/data.db"
```

The application uses Pydantic Settings to load environment variables from the `.env` file.

Follow the command from root of the repo
### Backend
```cmd
uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log
```

### Frontend
```cmd
uv run streamlit run src/frontend/chatbot_page.py
```
## Architecture

Frontend:
- Streamlit

Backend API:
- FastAPI

LLM Runtime:
- Ollama (local models)

Persistence (planned):
- SQLite → PostgreSQL (planned migration)

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
│   │   ├── api/                # FastAPI routers and API endpoints
│   │   ├── chat_bot/           # LLM/Ollama communication logic
│   │   ├── configuration/      # Settings and logging configuration
│   │   ├── database/           # SQLAlchemy models, engine and DB setup
│   │   ├── dependencies/       # FastAPI dependencies
│   │   ├── exceptions/         # Custom exceptions and handlers
│   │   ├── middleware/         # Request ID and logging middleware
│   │   ├── service/            # Business logic and orchestration layer
│   │   ├── __init__.py
│   │   └── main.py             # FastAPI application entrypoint
│   │
│   └── frontend/
│       └── chatbot_page.py     # Streamlit frontend application
│
├── tests/                      # Unit and integration tests
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml              # Project configuration and dependencies
└── uv.lock                     # Locked dependency versions
```

## Streaming Responses

The backend streams responses from Ollama through FastAPI StreamingResponse.

The Streamlit frontend consumes streamed chunks in real-time to simulate ChatGPT-like interaction.



## Current Features

- Local LLM chatbot using Ollama
- Streaming AI responses
- FastAPI backend API
- Streamlit frontend UI
- Chat history handled in frontend state
- Request tracing middleware
- Structured logging with Loguru
- Pydantic settings & validation
- Project managed with uv
- Installed as editable Python package
- Basic test suite
- Layered backend architecture
- Persistent chat history (SQLite)
- Multi-chat support (for one user -> user based after adding authentication)

## Planned Features

- JWT/O2Auth authentication
- PostgreSQL integration
- Redis-based conversational memory
- Voice input (speech-to-text)
- AI text-to-speech responses
- User metrics dashboard
- Grafana/Loki and Prometheus observability stack
- CI/CD with GitHub Actions
- Dockerized deployment
- RAG support


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