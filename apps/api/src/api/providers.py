"""Thin, uniform wrappers around each LLM provider's SDK.

Every provider exposes the same two functions so the rest of the app
never has to branch on `if provider == "Groq"` more than once:

    complete(model, messages, max_tokens)        -> str
    stream(model, messages, max_tokens)           -> Iterator[str]

Keeping this in one module also makes it trivial to add a new provider:
write the two functions, register them in PROVIDERS, done.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from google import genai
from groq import Groq

from api.core.config import config

logger = logging.getLogger(__name__)

DEFAULT_MAX_TOKENS = 500


class ProviderError(Exception):
    """Raised when an upstream provider call fails after retries."""


def _to_plain_messages(messages: list[dict]) -> list[dict]:
    """Strip any extra keys the UI might send and keep role/content only."""
    return [{"role": m["role"], "content": m["content"]} for m in messages]


# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------

def _groq_complete(model: str, messages: list[dict], max_tokens: int) -> str:
    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=_to_plain_messages(messages),
        max_completion_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def _groq_stream(model: str, messages: list[dict], max_tokens: int) -> Iterator[str]:
    client = Groq(api_key=config.GROQ_API_KEY)
    stream = client.chat.completions.create(
        model=model,
        messages=_to_plain_messages(messages),
        max_completion_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


# ---------------------------------------------------------------------------
# Google (Gemini)
# ---------------------------------------------------------------------------

def _google_complete(model: str, messages: list[dict], max_tokens: int) -> str:
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=[m["content"] for m in messages],
    )
    return response.text or ""


def _google_stream(model: str, messages: list[dict], max_tokens: int) -> Iterator[str]:
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    stream = client.models.generate_content_stream(
        model=model,
        contents=[m["content"] for m in messages],
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


# ---------------------------------------------------------------------------
# Registry + public entry points
# ---------------------------------------------------------------------------

PROVIDERS = {
    "Groq": {"complete": _groq_complete, "stream": _groq_stream},
    "Google": {"complete": _google_complete, "stream": _google_stream},
}

MAX_RETRIES = 2


def complete(provider: str, model: str, messages: list[dict], max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    if provider not in PROVIDERS:
        raise ProviderError(f"Unknown provider: {provider}")

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return PROVIDERS[provider]["complete"](model, messages, max_tokens)
        except Exception as exc:  # noqa: BLE001 - we deliberately catch broadly here
            last_error = exc
            logger.warning(
                "Provider %s call failed (attempt %s/%s): %s",
                provider, attempt, MAX_RETRIES, exc,
            )

    raise ProviderError(f"{provider} request failed after {MAX_RETRIES} attempts") from last_error


def stream(provider: str, model: str, messages: list[dict], max_tokens: int = DEFAULT_MAX_TOKENS) -> Iterator[str]:
    if provider not in PROVIDERS:
        raise ProviderError(f"Unknown provider: {provider}")

    try:
        yield from PROVIDERS[provider]["stream"](model, messages, max_tokens)
    except Exception as exc:  # noqa: BLE001
        logger.error("Provider %s stream failed: %s", provider, exc)
        raise ProviderError(f"{provider} streaming request failed") from exc
