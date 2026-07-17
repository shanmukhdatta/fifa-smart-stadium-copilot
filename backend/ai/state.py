"""
Shared state object threaded through every LangGraph node.

Using a single TypedDict keeps node signatures uniform (each node takes
CopilotState, returns a partial update) which is what LangGraph expects,
and keeps the whole pipeline easy to unit test -- you can construct a
CopilotState by hand and feed it directly into any node.
"""

from typing import TypedDict


class CopilotState(TypedDict, total=False):
    request_id: str
    user_id: str
    role: str

    raw_message: str
    language: str
    location: str | None
    accessibility_needs: list[str]
    chat_history: list[dict[str, str]]

    # planner output
    intent: str
    required_agents: list[str]

    # agent outputs, keyed by agent name
    agent_outputs: dict

    # retrieval
    rag_context: list[str]
    live_data: dict

    # fusion output
    fused_summary: str
    confidence: float

    # final
    response_text: str
    voice_ready_text: str

    # error propagation (validation / injection failures short-circuit here)
    error: str | None
