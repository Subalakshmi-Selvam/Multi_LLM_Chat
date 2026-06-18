# api

FastAPI backend that exposes a single chat interface over OpenAI, Anthropic,
Groq, and Google Gemini, plus SQLite-backed chat history.

See the [project README](../../README.md) for setup and API docs.

## Local dev

```bash
uv sync
uv run --package api uvicorn api.app:app --reload --app-dir src
```

## Tests

```bash
uv run pytest
```
