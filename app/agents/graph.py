from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    AgentState,
    analytics_tool_node,
    classify_node,
    live_tool_node,
    rag_tool_node,
    synthesize_node,
)


def _route_after_classify(state: AgentState) -> str:
    intent = state.get("intent", "KNOWLEDGE")
    return {
        "REALTIME": "live_tool",
        "KNOWLEDGE": "rag_tool",
        "HYBRID": "live_tool",
        "ANALYTICS": "analytics_tool",
    }.get(intent, "rag_tool")


def _route_after_live(state: AgentState) -> str:
    # HYBRID runs live first, then RAG
    if state.get("intent") == "HYBRID":
        return "rag_tool"
    return "synthesize"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("live_tool", live_tool_node)
    graph.add_node("rag_tool", rag_tool_node)
    graph.add_node("analytics_tool", analytics_tool_node)
    graph.add_node("synthesize", synthesize_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_after_classify,
        {"live_tool": "live_tool", "rag_tool": "rag_tool", "analytics_tool": "analytics_tool"},
    )
    graph.add_conditional_edges(
        "live_tool",
        _route_after_live,
        {"rag_tool": "rag_tool", "synthesize": "synthesize"},
    )
    graph.add_edge("rag_tool", "synthesize")
    graph.add_edge("analytics_tool", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
