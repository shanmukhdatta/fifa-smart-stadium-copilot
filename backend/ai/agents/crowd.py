from backend.ai.agents.base import BaseAgent


class CrowdAgent(BaseAgent):
    name = "crowd"
    system_prompt = (
        "You are the Crowd Intelligence Agent for a FIFA World Cup stadium "
        "copilot. Use the live crowd density data to recommend the least "
        "congested gate or route. Be brief and specific."
    )

    def build_context(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        gates = live_data.get("crowd", {}).get("gates", {})
        density_summary = ", ".join(f"{g}: {level}" for g, level in gates.items()) or "no data"
        history_str = self.format_history(chat_history)
        return (
            f"Conversation History:\n{history_str}\n\n"
            f"Fan question: {query}\n\n"
            f"Live gate crowd levels: {density_summary}"
        )

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        gates = live_data.get("crowd", {}).get("gates", {})
        low = [g for g, level in gates.items() if level == "low"]
        if low:
            return f"Current lowest-congestion option: {low[0]}. Consider heading there."
        return "Crowd levels are moderate to high across gates right now. Allow extra time."
