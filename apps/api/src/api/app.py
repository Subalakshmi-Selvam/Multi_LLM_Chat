import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api import history
from api.providers import ProviderError, complete, stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    history.init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="Multi-LLM Chat API", lifespan=lifespan)

# Streamlit runs in a separate container/origin in docker-compose, so CORS
# needs to be open for local/dev use. Tighten this to specific origins
# before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    provider: str
    model_name: str
    messages: list[ChatMessage]
    session_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: str


class SessionCreateRequest(BaseModel):
    title: str = "New chat"


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or history.create_session()
    messages = [m.model_dump() for m in payload.messages]

    try:
        result = complete(payload.provider, payload.model_name, messages)
    except ProviderError as exc:
        logger.error("Chat request failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    last_user_message = messages[-1] if messages else None
    if last_user_message and last_user_message["role"] == "user":
        history.add_message(session_id, "user", last_user_message["content"])
    history.add_message(
        session_id, "assistant", result, provider=payload.provider, model_name=payload.model_name
    )

    return ChatResponse(message=result, session_id=session_id)


@app.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    session_id = payload.session_id or history.create_session()
    messages = [m.model_dump() for m in payload.messages]

    def event_generator():
        collected = []
        try:
            for token in stream(payload.provider, payload.model_name, messages):
                collected.append(token)
                yield token
        except ProviderError as exc:
            logger.error("Streaming chat request failed: %s", exc)
            yield f"\n\n[error: {exc}]"
            return

        full_response = "".join(collected)
        last_user_message = messages[-1] if messages else None
        if last_user_message and last_user_message["role"] == "user":
            history.add_message(session_id, "user", last_user_message["content"])
        history.add_message(
            session_id, "assistant", full_response, provider=payload.provider, model_name=payload.model_name
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={"X-Session-Id": session_id},
    )


@app.post("/sessions", response_model=SessionResponse)
def create_session(payload: SessionCreateRequest) -> SessionResponse:
    session_id = history.create_session(title=payload.title)
    session = history.get_session(session_id)
    return SessionResponse(**session)


@app.get("/sessions")
def list_sessions() -> list[SessionResponse]:
    return [SessionResponse(**s) for s in history.list_sessions()]


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str) -> list[dict]:
    if history.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return history.get_messages(session_id)


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    if history.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    history.delete_session(session_id)
    return {"status": "deleted"}
