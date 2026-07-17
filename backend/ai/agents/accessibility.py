from backend.ai.agents.base import BaseAgent


class AccessibilityAgent(BaseAgent):
    name = "accessibility"
    system_prompt = (
        "You are the Accessibility Agent for a FIFA World Cup stadium "
        "copilot. Use the accessibility guide context to answer questions "
        "about wheelchair routing, accessible entrances, sensory-friendly "
        "spaces, and staff support. Be practical and reassuring."
    )

    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        knowledge = "\n".join(rag_context) or "No specific accessibility data retrieved."
        history_str = self.format_history(chat_history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"Fan question: {query}\n\n"
            f"Accessibility knowledge:\n{knowledge}"
        )

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        if rag_context:
            return "Accessibility info: " + rag_context[0][:280]
        return (
            "For accessibility support, head to Gate 3, which has ramp and "
            "elevator access, or ask any staff member to call an "
            "accessibility coordinator."
        )
