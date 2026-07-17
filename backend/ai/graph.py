"""
Assembles the LangGraph pipeline:

  validate_input -> planner -> knowledge_and_live_data -> parallel_agents
  -> decision_fusion -> response_generation -> END

Any node can set state["error"], and downstream nodes short-circuit to a
no-op update, so an invalid/blocked request still flows cleanly to
response_generation, which turns the error into a safe user-facing
message instead of throwing.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.ai.nodes import (
    decision_fusion_node,
    knowledge_and_live_data_node,
    parallel_agents_node,
    planner_node,
    response_generation_node,
    validate_input_node,
)
from backend.ai.state import CopilotState


def build_graph():
    graph = StateGraph(CopilotState)

    graph.add_node("validate_input", validate_input_node)
    graph.add_node("planner", planner_node)
    graph.add_node("knowledge_and_live_data", knowledge_and_live_data_node)
    graph.add_node("parallel_agents", parallel_agents_node)
    graph.add_node("decision_fusion", decision_fusion_node)
    graph.add_node("response_generation", response_generation_node)

    graph.set_entry_point("validate_input")
    graph.add_edge("validate_input", "planner")
    graph.add_edge("planner", "knowledge_and_live_data")
    graph.add_edge("knowledge_and_live_data", "parallel_agents")
    graph.add_edge("parallel_agents", "decision_fusion")
    graph.add_edge("decision_fusion", "response_generation")
    graph.add_edge("response_generation", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
