# ADR 0001: Run Ollama natively instead of in Docker Compose

**Status:** Accepted  
**Date:** 2026-10-27  
**Decision:** Run Ollama natively on the host computer. Containerize the
Streamlit frontend, FastAPI backend, and PostgreSQL with Docker Compose.

## Context

The original goal was to run the complete application in Docker Compose,
including the LLM. Before committing to that design, two questions had to be
answered:

1. Does Ollama in a container provide good performance on an Apple Silicon
   computer?
2. Can Docker Model Runner (DMR) replace Ollama directly without reducing the
   application's capabilities?

At this stage, both options introduce significant trade-offs. The application
therefore containerizes the application services and database, while Ollama
remains a native service on the user's computer.

## Decision

```text
Docker Compose
├── frontend (Streamlit)
├── backend  (FastAPI + Chroma)
└── postgres (conversation history and file metadata)

User's host
└── Ollama :11434 (models and native Apple GPU use)
```

The backend receives the Ollama address through `OLLAMA_API`. For Docker
Desktop on macOS and Windows, use:

```env
OLLAMA_API=http://host.docker.internal:11434
```

A container cannot use `localhost:11434`, because `localhost` inside a
container refers to that container rather than the host computer. The backend
passes this configuration to both `ChatOllama` and `OllamaEmbeddings`, so
response generation, conversation-title generation, the model list, and RAG
all use the same native Ollama instance.

## Evidence and alternatives considered

### Ollama in Docker on macOS

During testing, Ollama running in a container consumed substantial CPU while
generating responses. Its RAM usage also grew enough for the process to be
killed by the Linux out-of-memory mechanism inside Docker Desktop.

On macOS, Docker Desktop does not expose the Apple Silicon GPU to containers.
Native Ollama can use the Apple GPU, whereas the same Ollama instance in a
container runs primarily on the CPU. GPU acceleration in a container can be
possible on a properly configured NVIDIA machine or Windows with WSL2, but
that does not solve the current macOS use case.

References:

- [Ollama FAQ: GPU acceleration in Docker](https://github.com/ollama/ollama/blob/main/docs/faq.mdx#how-do-i-use-ollama-with-gpu-acceleration-in-docker)
- [Ollama issue #3849: Apple GPU and Docker Desktop](https://github.com/ollama/ollama/issues/3849)

### Docker Model Runner

DMR was considered as a way to keep model execution in the Docker ecosystem
without an Ollama container. Testing the embeddings endpoint showed an API
version mismatch:

```bash
curl -i http://localhost:12434/api/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"ai/embeddinggemma","input":"Hello world"}'
# HTTP/1.1 404 Not Found
```

The current `langchain-ollama` wrapper uses Ollama's newer `/api/embed`
endpoint. The tested DMR version did not support that endpoint, but did respond
to this older compatible endpoint:

```text
http://localhost:12434/engines/v1/embeddings
```

A possible workaround would be to use `OpenAIEmbeddings` against the older
endpoint. That would require changing the embedding client and could sacrifice
benefits of the newer API, including more convenient batching while indexing
documents.

The application deliberately passes settings such as `temperature`, `top_k`,
`top_p`, `num_ctx`, `num_predict`, `repeat_penalty`, and `reasoning` with every
request. This lets users observe how the parameters affect a model's response.
DMR did not expose the same parameter set per request; some settings would
need to be configured when the model is set up. Without changing the
application's UX and code, this would be a regression.

## Consequences

Benefits:

- models can use the GPU on Apple Silicon;
- there is no additional LLM container with a large RAM and CPU footprint;
- the current Ollama endpoints and per-request generation parameters are
  preserved;
- PostgreSQL, uploads, and the vector database are still reproducibly started
  by Compose and stored in volumes.

Costs:

- users must install Ollama and download a conversation model and embedding
  model themselves;
- Ollama must be running on port `11434` before the application starts;
- the deployment is not yet a fully self-contained, one-command
  `docker compose up` package;
- configuration differs between native execution (`localhost`) and container
  execution (`host.docker.internal`).

## When to revisit this decision

Revisit DMR when its embeddings API and per-request parameter support meet the
application's requirements. Before migrating, test the current DMR endpoints,
compare indexing quality and time, and decide whether changing the embedding
wrapper and restricting the UI parameters is acceptable.
