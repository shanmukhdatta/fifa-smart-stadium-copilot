"""
Base class all stadium agents inherit from.

Each agent is:
  - stateless (no shared mutable state between calls)
  - asynchronous (so the orchestrator can run all of them with
    asyncio.gather for real parallelism, not just async syntax)
  - independently unit-testable (build_context + synthesize can be tested
    without the LLM or FastAPI running)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.ai.llm_client import LLMUnavailableError, complete
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

__all__ = ["BaseAgent"]


class BaseAgent(ABC):
    name: str = "base"
    system_prompt: str = "You are a helpful stadium assistant."

    def format_history(self, chat_history: list[dict] | None) -> str:
        if not chat_history:
            return "No previous conversation history."
        lines = []
        for msg in chat_history:
            role = "Fan" if msg["role"] == "user" else "Copilot"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def build_prompt_block(
        self,
        query: str,
        knowledge: list[str],
        chat_history: list[dict] | None,
        knowledge_label: str = "Retrieved knowledge",
        no_knowledge_text: str = "No specific data retrieved.",
    ) -> str:
        """Shared prompt-assembly used by every agent's build_context to avoid logic duplication."""
        knowledge_str = "\n".join(knowledge) or no_knowledge_text
        history_str = self.format_history(chat_history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"Fan question: {query}\n\n"
            f"{knowledge_label}:\n{knowledge_str}"
        )

    @abstractmethod
    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        """Turn retrieved knowledge + live data into a compact prompt context."""

    @abstractmethod
    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        """Deterministic, template-based answer used if the LLM is unavailable."""

    async def run(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> dict:
        context = self.build_context(query, rag_context, live_data, chat_history)
        try:
            text = await complete(self.system_prompt, context)
            confidence = 0.9
        except LLMUnavailableError:
            text = self.fallback_response(query, rag_context, live_data, chat_history)
            confidence = 0.6  # lower confidence for the template fallback path
        return {
            "agent": self.name,
            "summary": text,
            "confidence": confidence,
        }
