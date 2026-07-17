from backend.ai.agents.base import BaseAgent

__all__ = ["NavigationAgent"]


class NavigationAgent(BaseAgent):
    name = "navigation"
    system_prompt = (
        "You are the Navigation Agent for a FIFA World Cup stadium copilot. "
        "Give concise, step-by-step directions using the stadium map context "
        "provided. Mention the nearest gate, restrooms, or food stalls only "
        "if relevant to the question."
    )

    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        return self.build_prompt_block(query, rag_context, chat_history, "Stadium map knowledge")

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        if rag_context:
            return (
                "Based on the stadium map: " + rag_context[0][:280]
            )
        return (
            "I couldn't find a specific route for that. Please head to the "
            "nearest staff member in a teal vest for directions."
        )
