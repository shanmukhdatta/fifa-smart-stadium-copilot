"""Main copilot chat endpoint."""

import uuid

from fastapi import APIRouter, Depends, Request

from backend.ai.graph import get_graph
from backend.core.cache import TTLCache
from backend.core.logging_config import get_logger
from backend.core.rate_limit import limiter
from backend.core.security import get_current_user, redact
from backend.schemas.chat import AgentResult, ChatRequest, ChatResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["copilot"])

_session_cache = TTLCache(ttl_seconds=1800)  # 30 min idle session expiry


def _get_history(user_id: str) -> list[dict]:
    return _session_cache.get(user_id) or []


def _save_history(user_id: str, history: list[dict]) -> None:
    _session_cache.set(user_id, history[-10:])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    request_id = str(uuid.uuid4())
    user_id = user["user_id"]
    logger.info(
        "chat request_id=%s user=%s role=%s message=%s",
        request_id,
        user_id,
        user["role"],
        redact(payload.message),
    )

    history = _get_history(user_id)

    graph = get_graph()
    initial_state = {
        "request_id": request_id,
        "user_id": user_id,
        "role": user["role"],
        "raw_message": payload.message,
        "language": payload.normalized_language(),
        "location": payload.location,
        "accessibility_needs": payload.accessibility_needs,
        "chat_history": list(history),
    }

    result = await graph.ainvoke(initial_state)

    # Save current turn to session history
    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": result.get("response_text", "")})
    _save_history(user_id, history)

    agent_results = [
        AgentResult(
            agent=name,
            summary=out["summary"],
            confidence=out["confidence"],
            details={},
        )
        for name, out in result.get("agent_outputs", {}).items()
    ]

    return ChatResponse(
        response_text=result.get("response_text", ""),
        language=result.get("language", "en"),
        agents_used=result.get("required_agents", []),
        agent_results=agent_results,
        voice_ready_text=result.get("voice_ready_text", ""),
        confidence=result.get("confidence", 0.0),
        request_id=request_id,
    )
