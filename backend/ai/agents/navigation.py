from backend.ai.agents.base import BaseAgent


class NavigationAgent(BaseAgent):
    name = "navigation"
    system_prompt = (
        "You are the Navigation Agent for a FIFA World Cup stadium copilot. "
        "Give concise, step-by-step directions using the stadium map context "
        "provided. Mention the nearest gate, restrooms, or food stalls only "
        "if relevant to the question."
    )

    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        knowledge = "\n".join(rag_context) or "No specific map data retrieved."
        history_str = self.format_history(chat_history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"Fan question: {query}\n\n"
            f"Stadium map knowledge:\n{knowledge}"
        )

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        if rag_context:
            return (
                "Based on the stadium map: " + rag_context[0][:280]
            )
        return (
            "I couldn't find a specific route for that. Please head to the "
            "nearest staff member in a teal vest for directions."
        )
