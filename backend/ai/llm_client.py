"""
Thin wrapper around the LLM provider.

Two things this buys us:
1. Every call site is testable -- tests monkeypatch `complete()` instead of
   mocking httpx internals.
2. Graceful degradation. If the API key is a placeholder, or the network
   call fails/times out, callers fall back to deterministic template
   responses instead of the whole request failing. This matters a lot in
   a live demo where flaky wifi shouldn't take the app down.
"""

from __future__ import annotations

import httpx

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

_PLACEHOLDER_KEY = "sk-placeholder-for-local-dev"


_HTTP_CLIENT: httpx.AsyncClient | None = None


def _get_client(timeout: float) -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        # Reuses connections across requests for efficiency (Connection Pooling)
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _HTTP_CLIENT


class LLMUnavailableError(Exception):
    """Raised when no real LLM call could be made -- callers should fall back."""


async def complete(system_prompt: str, user_prompt: str, timeout: float = 8.0) -> str:
    if settings.openai_api_key == _PLACEHOLDER_KEY:
        raise LLMUnavailableError("No LLM API key configured")

    client = _get_client(timeout)
    try:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, this is a fallback boundary
        logger.warning("LLM call failed, falling back to template response: %s", exc)
        raise LLMUnavailableError(str(exc)) from exc
