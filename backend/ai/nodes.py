"""
LangGraph node functions. Each takes the shared CopilotState and returns a
partial dict update (LangGraph merges it in) -- this keeps every node a
small, pure-ish, independently testable function.
"""

from __future__ import annotations

import asyncio

from backend.ai import live_data as live_data_source
from backend.ai.agents.accessibility import AccessibilityAgent
from backend.ai.agents.crowd import CrowdAgent
from backend.ai.agents.emergency import EmergencyAgent
from backend.ai.agents.navigation import NavigationAgent
from backend.ai.planner import detect_intent_and_agents
from backend.ai.rag.retriever import get_retriever
from backend.ai.state import CopilotState
from backend.core.cache import live_data_cache, rag_cache
from backend.core.logging_config import get_logger
from backend.core.security import PromptInjectionError, check_prompt_injection, validate_output

logger = get_logger(__name__)

_AGENTS = {
    "navigation": NavigationAgent(),
    "crowd": CrowdAgent(),
    "accessibility": AccessibilityAgent(),
    "emergency": EmergencyAgent(),
}


def validate_input_node(state: CopilotState) -> dict:
    message = state.get("raw_message", "")
    if not message.strip():
        return {"error": "Empty message"}
    try:
        check_prompt_injection(message)
    except PromptInjectionError as exc:
        return {"error": str(exc)}
    return {"error": None}


async def planner_node(state: CopilotState) -> dict:
    if state.get("error"):
        return {"error": state.get("error")}
    intent, agents = await detect_intent_and_agents(state["raw_message"])
    logger.info("Planner selected intent=%s agents=%s", intent, agents)
    return {"intent": intent, "required_agents": agents}


def knowledge_and_live_data_node(state: CopilotState) -> dict:
    if state.get("error"):
        return {"error": state.get("error")}

    query = state["raw_message"]
    cache_key = f"rag:{query.lower().strip()}"
    cached = rag_cache.get(cache_key)
    if cached is not None:
        rag_chunks = cached
    else:
        retriever = get_retriever()
        results = retriever.search(query, top_k=3)
        rag_chunks = [r["text"] for r in results]
        rag_cache.set(cache_key, rag_chunks)

    live = live_data_cache.get("live_snapshot")
    if live is None:
        live = {
            "crowd": live_data_source.get_crowd_density(),
            "weather": live_data_source.get_weather(),
            "parking": live_data_source.get_parking_availability(),
            "transport": live_data_source.get_transport_status(),
        }
        live_data_cache.set("live_snapshot", live)

    return {"rag_context": rag_chunks, "live_data": live}


async def parallel_agents_node(state: CopilotState) -> dict:
    if state.get("error"):
        return {"error": state.get("error")}

    required = state.get("required_agents", []) or ["navigation"]
    query = state["raw_message"]
    rag_context = state.get("rag_context", [])
    live = state.get("live_data", {})

    tasks = [_AGENTS[name].run(query, rag_context, live, state.get("chat_history")) for name in required if name in _AGENTS]
    results = await asyncio.gather(*tasks)

    outputs = {r["agent"]: r for r in results}
    return {"agent_outputs": outputs}


def decision_fusion_node(state: CopilotState) -> dict:
    if state.get("error"):
        return {"error": state.get("error")}

    outputs = state.get("agent_outputs", {})
    if not outputs:
        return {"fused_summary": "", "confidence": 0.0}

    # Priority ranking: emergency output always wins if present.
    if "emergency" in outputs:
        chosen = [outputs["emergency"]]
    else:
        chosen = list(outputs.values())

    # Confidence scoring: average across contributing agents.
    avg_confidence = sum(o["confidence"] for o in chosen) / len(chosen)

    # Merge agent outputs into one fused summary.
    fused = "\n\n".join(f"[{o['agent'].title()}] {o['summary']}" for o in chosen)

    return {"fused_summary": fused, "confidence": round(avg_confidence, 2)}


async def translate_text(text: str, target_lang: str) -> str:
    from backend.ai.llm_client import complete
    lang_names = {
        "es": "Spanish",
        "fr": "French",
        "ar": "Arabic",
        "pt": "Portuguese",
        "hi": "Hindi",
    }
    target_name = lang_names.get(target_lang, "English")
    system_prompt = (
        f"You are a professional translator. Translate the following text into {target_name}. "
        "Maintain all bracketed labels (like [Navigation], [Crowd], [Accessibility], [Emergency]) exactly as they are in the source text. "
        "Do not add any additional explanation, and output only the direct translation."
    )
    return await complete(system_prompt, text, timeout=4.0)


_LANGUAGE_PREFIX = {
    "en": "",
    "es": "(Respuesta traducida) ",
    "fr": "(Réponse traduite) ",
    "ar": "(رد مترجم) ",
    "pt": "(Resposta traduzida) ",
    "hi": "(अनुवादित उत्तर) ",
}


async def response_generation_node(state: CopilotState) -> dict:
    if state.get("error"):
        return {
            "response_text": state["error"],
            "voice_ready_text": state["error"],
        }

    language = state.get("language", "en")
    summary = state.get("fused_summary") or "I don't have enough information to answer that yet."

    response_text = summary
    if language != "en" and language in {"es", "fr", "ar", "pt", "hi"}:
        try:
            response_text = await translate_text(summary, language)
        except Exception as exc:
            logger.warning("Translation failed, falling back to prefix warning: %s", exc)
            prefix = _LANGUAGE_PREFIX.get(language, "")
            response_text = f"{prefix}{summary}"

    # Run through output validator & hallucination guardrails
    response_text = validate_output(response_text)

    # Voice-ready text strips bracketed agent labels for cleaner TTS output.
    voice_text = response_text
    for label in ["[Navigation] ", "[Crowd] ", "[Accessibility] ", "[Emergency] ", "[Navigation]", "[Crowd]", "[Accessibility]", "[Emergency]"]:
        voice_text = voice_text.replace(label, "")

    return {"response_text": response_text, "voice_ready_text": voice_text}
