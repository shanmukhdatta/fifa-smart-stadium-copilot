from backend.ai.agents.base import BaseAgent

__all__ = ["CrowdAgent"]


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
        return self.build_prompt_block(query, [density_summary], chat_history, "Live gate crowd levels")

    def fallback_response(self, query: str, rag_context: list[str], live_data: dict, chat_history: list[dict] | None = None) -> str:
        gates = live_data.get("crowd", {}).get("gates", {})
        low = [g for g, level in gates.items() if level == "low"]
        if low:
            return f"Current lowest-congestion option: {low[0]}. Consider heading there."
        return "Crowd levels are moderate to high across gates right now. Allow extra time."
