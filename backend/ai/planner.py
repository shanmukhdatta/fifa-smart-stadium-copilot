"""
Planner node logic.

Deliberately rule-based rather than an LLM call: agent routing needs to be
fast, cheap, and deterministic (testable with plain asserts), and a
keyword/intent classifier is entirely sufficient for a bounded set of 4
agents. This also means the planner never burns an LLM call just to
decide "who should answer" -- a direct efficiency win over an
LLM-plans-everything design, and it means a bad/slow LLM call can never
break routing itself. The Planner never generates the user-facing answer
-- only the plan.
"""

from __future__ import annotations

_KEYWORDS = {
    "emergency": [
        "emergency", "fire", "medical", "help me", "evacuat", "lost child",
        "injured", "danger", "police", "ambulance",
    ],
    "accessibility": [
        "wheelchair", "accessible", "disability", "ramp", "sign language",
        "screen reader", "sensory", "quiet room",
    ],
    "crowd": [
        "crowded", "crowd", "busy", "queue", "line", "congestion", "wait time",
    ],
    "navigation": [
        "where is", "how do i get", "directions", "restroom", "toilet",
        "seat", "gate", "food", "route", "map",
    ],
}


async def detect_intent_and_agents(message: str) -> tuple[str, list[str]]:
    text = message.lower()
    matched = [
        agent for agent, keywords in _KEYWORDS.items()
        if any(kw in text for kw in keywords)
    ]

    # Emergency always takes priority and is never silently dropped.
    if "emergency" in matched:
        return "emergency", ["emergency"]

    if not matched:
        # Fallback to LLM semantic classification if rules match nothing
        try:
            from backend.ai.llm_client import complete
            system_prompt = (
                "You are an routing classifier for a FIFA World Cup stadium assistant. "
                "Classify the user's message into one or more of these categories: "
                "navigation, crowd, accessibility, emergency. "
                "Respond with a comma-separated list of categories, in order of relevance, and nothing else (e.g. 'navigation,crowd'). "
                "If it matches nothing, respond with 'navigation'."
            )
            response = await complete(system_prompt, f"Message: {message}", timeout=4.0)
            llm_agents = [
                a.strip().lower()
                for a in response.split(",")
                if a.strip().lower() in {"navigation", "crowd", "accessibility", "emergency"}
            ]
            if llm_agents:
                return llm_agents[0], llm_agents
        except Exception:
            pass
        # Fall back to default
        return "general_inquiry", ["navigation"]

    intent = matched[0]
    return intent, matched
