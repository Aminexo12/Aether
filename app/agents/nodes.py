import json
import operator
from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.agents.prompts import CLASSIFIER_SYSTEM, SYNTHESIZER_SYSTEM
from app.config import settings
from app.data.models import BBOX_EUROPE
from app.data.opensky import OpenSkyClient
from app.rag.retrieve import search_docs


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    tool_results: Annotated[list[str], operator.add]


async def classify_node(state: AgentState) -> dict:
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=settings.anthropic_api_key, max_tokens=128)
    user_msg = state["messages"][-1].content
    response = await llm.ainvoke([
        SystemMessage(content=CLASSIFIER_SYSTEM),
        HumanMessage(content=str(user_msg)),
    ])
    try:
        raw = str(response.content).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        intent = data.get("intent", "KNOWLEDGE").upper()
    except (json.JSONDecodeError, AttributeError, KeyError):
        intent = "KNOWLEDGE"

    if intent not in {"REALTIME", "KNOWLEDGE", "HYBRID", "ANALYTICS"}:
        intent = "KNOWLEDGE"

    return {"intent": intent}


async def live_tool_node(state: AgentState) -> dict:
    client = OpenSkyClient()
    try:
        flights = await client.get_flights(BBOX_EUROPE)
    finally:
        await client.close()

    airborne = [f for f in flights if not f.on_ground]
    top5 = sorted(
        [f for f in airborne if f.velocity],
        key=lambda f: f.velocity,  # type: ignore[arg-type]
        reverse=True,
    )[:5]

    lines = [f"**Live flights over Europe:** {len(airborne)} airborne, {len(flights) - len(airborne)} on ground"]
    if top5:
        lines.append("\n**Fastest aircraft right now:**")
        for f in top5:
            speed = f.velocity * 3.6 if f.velocity else 0
            alt = f.baro_altitude or 0
            lines.append(f"- {f.callsign or f.icao24} ({f.origin_country}) — {speed:.0f} km/h at {alt:.0f} m")

    return {"tool_results": ["\n".join(lines)]}


async def rag_tool_node(state: AgentState) -> dict:
    query = str(state["messages"][-1].content)
    results = search_docs(query, collection=settings.qdrant_collection, top_k=5)

    if not results:
        return {"tool_results": ["No relevant documentation found for this query."]}

    lines = ["**Aviation documentation search results:**"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n[{i}] *{r.source}*, page {r.page} (relevance: {r.score:.2f})")
        lines.append(r.text[:600])

    return {"tool_results": ["\n".join(lines)]}


async def analytics_tool_node(state: AgentState) -> dict:
    client = OpenSkyClient()
    try:
        flights = await client.get_flights(BBOX_EUROPE)
    finally:
        await client.close()

    airborne = [f for f in flights if not f.on_ground]
    speeds = [f.velocity * 3.6 for f in airborne if f.velocity]
    altitudes = [f.baro_altitude for f in airborne if f.baro_altitude]

    country_counts: dict[str, int] = {}
    for f in flights:
        country_counts[f.origin_country] = country_counts.get(f.origin_country, 0) + 1
    top5 = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    avg_alt = sum(altitudes) / len(altitudes) if altitudes else 0

    lines = [
        "**Traffic analytics — Europe (live snapshot):**",
        f"- Total aircraft tracked: {len(flights)}",
        f"- Airborne: {len(airborne)} ({len(airborne)/max(len(flights),1)*100:.1f}%)",
        f"- Average speed: {avg_speed:.0f} km/h",
        f"- Average altitude: {avg_alt:.0f} m",
        f"- Top countries: {', '.join(f'{c} ({n})' for c, n in top5)}",
    ]

    return {"tool_results": ["\n".join(lines)]}


async def synthesize_node(state: AgentState) -> dict:
    llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=settings.anthropic_api_key, max_tokens=1024)
    user_msg = str(state["messages"][-1].content)
    context = "\n\n---\n\n".join(state.get("tool_results") or ["No tool data available."])

    prompt = f"""Context retrieved from tools:

{context}

---

User question: {user_msg}

Answer the question using the context above. Cite sources when quoting documentation."""

    response = await llm.ainvoke([
        SystemMessage(content=SYNTHESIZER_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return {"messages": [AIMessage(content=str(response.content))]}
