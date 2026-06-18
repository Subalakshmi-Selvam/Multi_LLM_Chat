# Multi-LLM Chat Platform

A small full-stack reference app for working with multiple LLM providers
behind one consistent API: a FastAPI backend that normalizes OpenAI, Groq,
Google Gemini, and Anthropic Claude into a single interface, and a Streamlit
chat UI on top of it with persistent history and streaming responses.

Built while practicing AI engineering fundamentals — provider abstraction,
streaming, retries, and a thin persistence layer — packaged as a runnable
two-service Docker Compose stack.

## Features

- **Four providers, one interface** — OpenAI, Anthropic, Groq, and Google
  Gemini are all driven through the same `complete()` / `stream()` functions
  in [`providers.py`](apps/api/src/api/providers.py), so adding a fifth
  provider means writing two functions and registering them.
- **Streaming responses** — tokens are streamed from the provider straight
  through to the browser via a `StreamingResponse` endpoint, rendered live
  in the Streamlit UI.
- **Persistent chat history** — conversations are stored in SQLite
  (session + message tables) so previous chats survive a page reload or
  container restart; the sidebar lists past sessions and reloads them on
  click.
- **Retries + error handling** — provider calls retry transient failures
  and surface clean errors (HTTP 502 with a message) instead of leaking
  stack traces to the client.
- **Health check + Compose wiring** — the API exposes `/health`, and
  `docker-compose.yml` uses it so the UI container only starts once the API
  is actually ready.
- **Tests** — `pytest` coverage for the history layer and the session
  endpoints, using FastAPI's `TestClient` against an isolated SQLite file.

## Architecture

```
┌───────────────────┐        HTTP        ┌────────────────────┐       SDK calls       ┌───────────────────────┐
│   Streamlit UI     │ ─────────────────▶ │   FastAPI API       │ ────────────────────▶ │ OpenAI / Anthropic /   │
│ (apps/chatbot_ui)  │ ◀──── stream ───── │   (apps/api)         │                       │ Groq / Google Gemini   │
└───────────────────┘                    └────────────────────┘                       └───────────────────────┘
                                                    │
                                                    ▼
                                            ┌──────────────┐
                                            │    SQLite     │
                                            │ chat_history  │
                                            └──────────────┘
```

This is a `uv` workspace with two installable packages under `apps/`:

```
apps/
├── api/            # FastAPI backend — provider abstraction, history, endpoints
│   ├── src/api/
│   │   ├── app.py        # routes
│   │   ├── providers.py  # OpenAI / Anthropic / Groq / Google wrappers
│   │   ├── history.py    # SQLite persistence
│   │   └── core/config.py
│   └── tests/
└── chatbot_ui/     # Streamlit frontend
    └── src/chatbot_ui/
        ├── app.py
        └── core/config.py
notebooks/prerequisites/   # exploratory notebook used while building this out
documentation/              # dev environment setup notes
```

## Getting started

### Prerequisites

- Docker + Docker Compose
- [`uv`](https://github.com/astral-sh/uv) (for running things outside Docker, e.g. tests)
- API keys for whichever providers you want to use

### 1. Configure environment variables

```bash
cp .env.example .env
```

Then fill in `.env` with your own keys:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...
GOOGLE_API_KEY=...
```

You don't need keys for every provider — just the ones you plan to use from
the model dropdown. Calling a provider without a configured key will return
an error from that provider's SDK, surfaced as a chat error message.

### 2. Run with Docker Compose

```bash
make run-docker-compose
```

This builds both images and starts:

- API at [http://localhost:8000](http://localhost:8000) (docs at `/docs`)
- Streamlit UI at [http://localhost:8501](http://localhost:8501)

Chat history persists in a named Docker volume (`chat-history-data`), so it
survives `docker compose down` / `up` cycles. Remove the volume to reset it.

### 3. Run locally without Docker (optional)

```bash
uv sync
uv run --package api uvicorn api.app:app --reload --app-dir apps/api/src
uv run --package chatbot_ui streamlit run apps/chatbot_ui/src/chatbot_ui/app.py
```

### Running tests

```bash
cd apps/api
uv run pytest
```

### A note on `uv.lock`

This repo doesn't ship a committed `uv.lock` — `uv sync` will generate one
locally on first run based on `pyproject.toml`. Commit it once you've run
`uv sync` if you want fully reproducible installs across machines.

## API overview

| Method | Path                          | Description                                  |
|--------|-------------------------------|-----------------------------------------------|
| GET    | `/health`                     | Liveness check                                |
| POST   | `/chat`                       | Non-streaming chat completion                |
| POST   | `/chat/stream`                | Streaming chat completion (plain text chunks) |
| POST   | `/sessions`                   | Create a new chat session                     |
| GET    | `/sessions`                   | List sessions, most recent first              |
| GET    | `/sessions/{id}/messages`     | Get full message history for a session        |
| DELETE | `/sessions/{id}`              | Delete a session and its messages             |

Full interactive docs are available at `/docs` once the API is running
(FastAPI's auto-generated Swagger UI).

## Notes on scope

This is intentionally a small, single-instance project — SQLite rather than
Postgres, no auth, no rate limiting. It's meant to demonstrate clean
provider abstraction, streaming, and a usable Docker Compose setup rather
than be production-hardened. Natural next steps if extending it:

- Swap SQLite for Postgres + SQLAlchemy if running more than one API replica
- Add request auth (API key or OAuth) before exposing this beyond localhost
- Add per-provider rate limiting / token budget tracking

## License

MIT — add a `LICENSE` file if you publish this under that license.
