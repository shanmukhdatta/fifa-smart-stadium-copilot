from backend.ai.agents.base import BaseAgent

__all__ = ["EmergencyAgent"]


class EmergencyAgent(BaseAgent):
    name = "emergency"
    system_prompt = (
        "You are the Emergency Response Agent for a FIFA World Cup stadium "
        "copilot. Use the emergency SOP context to give clear, calm, "
        "actionable safety instructions. Never speculate beyond the "
        "provided SOPs. If the situation sounds life-threatening, always "
        "tell the user to alert the nearest steward or call emergency "
        "services immediately."
    )

    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        knowledge = "\n".join(rag_context) or "No specific SOP retrieved."
        history_str = self.format_history(chat_history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"Fan question: {query}\n\n"
            f"Emergency SOP knowledge:\n{knowledge}"
        )

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        base = (
            "If this is a medical emergency, alert the nearest steward or "
            "call the on-site medical line immediately. "
        )
        if rag_context:
            base += rag_context[0][:200]
        return base
