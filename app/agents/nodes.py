import csv
import json
import operator
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.agents.prompts import CLASSIFIER_SYSTEM, SYNTHESIZER_SYSTEM
from app.config import settings
from app.data.models import (
    BBOX_AUSTRIA,
    BBOX_BELGIUM,
    BBOX_CZECHIA,
    BBOX_DENMARK,
    BBOX_EUROPE,
    BBOX_FRANCE,
    BBOX_GERMANY,
    BBOX_GREECE,
    BBOX_IRELAND,
    BBOX_ITALY,
    BBOX_NETHERLANDS,
    BBOX_NORWAY,
    BBOX_POLAND,
    BBOX_PORTUGAL,
    BBOX_SPAIN,
    BBOX_SWEDEN,
    BBOX_SWITZERLAND,
    BBOX_UK,
    BBOX_WORLD,
    BoundingBox,
)
from app.data.opensky import OpenSkyClient
from app.ml.anomaly import detect
from app.rag.retrieve import search_docs

_REGION_MAP: list[tuple[list[str], BoundingBox, str]] = [
    (["france", "french", "paris", "bordeaux", "marseille", "lyon", "nice"], BBOX_FRANCE,      "France"),
    (["spain", "spanish", "madrid", "barcelona", "seville", "iberia"],       BBOX_SPAIN,       "Spain"),
    (["germany", "german", "berlin", "munich", "frankfurt", "hamburg"],      BBOX_GERMANY,     "Germany"),
    (["uk", "united kingdom", "britain", "british", "london", "heathrow",
      "manchester", "gatwick"],                                               BBOX_UK,          "the UK"),
    (["italy", "italian", "rome", "milan", "venice", "naples"],              BBOX_ITALY,       "Italy"),
    (["belgium", "belgian", "brussels", "antwerp", "liege", "charleroi"],    BBOX_BELGIUM,     "Belgium"),
    (["netherlands", "dutch", "holland", "amsterdam", "schiphol",
      "rotterdam", "eindhoven"],                                              BBOX_NETHERLANDS, "the Netherlands"),
    (["switzerland", "swiss", "zurich", "geneva", "basel", "bern"],          BBOX_SWITZERLAND, "Switzerland"),
    (["austria", "austrian", "vienna", "salzburg", "innsbruck", "graz"],     BBOX_AUSTRIA,     "Austria"),
    (["poland", "polish", "warsaw", "krakow", "gdansk", "wroclaw"],          BBOX_POLAND,      "Poland"),
    (["greece", "greek", "athens", "thessaloniki", "heraklion"],             BBOX_GREECE,      "Greece"),
    (["portugal", "portuguese", "lisbon", "porto", "faro"],                  BBOX_PORTUGAL,    "Portugal"),
    (["ireland", "irish", "dublin", "cork", "shannon"],                      BBOX_IRELAND,     "Ireland"),
    (["czech", "czechia", "prague", "brno", "ostrava"],                      BBOX_CZECHIA,     "Czechia"),
    (["sweden", "swedish", "stockholm", "gothenburg", "malmo"],              BBOX_SWEDEN,      "Sweden"),
    (["norway", "norwegian", "oslo", "bergen", "trondheim", "stavanger"],    BBOX_NORWAY,      "Norway"),
    (["denmark", "danish", "copenhagen", "aarhus", "billund"],               BBOX_DENMARK,     "Denmark"),
    (["world", "global", "worldwide"],                                        BBOX_WORLD,       "the world"),
]

_DATA_DIR = Path(__file__).parent.parent / "data"


@lru_cache(maxsize=1)
def _load_airline_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Returns (icao3→name, name_lower→icao3)."""
    icao_to_name: dict[str, str] = {}
    name_to_icao: dict[str, str] = {}
    with open(_DATA_DIR / "airlines.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 7:
                continue
            icao3 = row[4].strip()
            name = row[1].strip()
            if not icao3 or icao3 == r"\N" or icao3 == "-" or not name:
                continue
            icao_to_name[icao3.upper()] = name
            name_to_icao[name.lower()] = icao3.upper()
    return icao_to_name, name_to_icao


def _airline_from_message(msg: str) -> tuple[str, str] | None:
    """Returns (icao3, display_name) if an airline name is found in the message."""
    _, name_to_icao = _load_airline_maps()
    icao_to_name, _ = _load_airline_maps()
    lower = msg.lower()
    best: tuple[str, str] | None = None
    best_len = 0
    for name_lower, icao3 in name_to_icao.items():
        # Skip data-error entries in OpenFlights (e.g. name="L", "88", "Zz").
        # These short strings false-match common English substrings — "l" inside
        # "flights" would otherwise filter every query by ICAO "LPR"/"LAU".
        if len(name_lower) < 4:
            continue
        # Word-boundary match so "tam" doesn't trigger on "Vietnam", etc.
        if re.search(rf"\b{re.escape(name_lower)}\b", lower) and len(name_lower) > best_len:
            best = (icao3, icao_to_name.get(icao3, name_lower.title()))
            best_len = len(name_lower)
    return best


def _region_from_message(msg: str) -> tuple[BoundingBox, str]:
    lower = msg.lower()
    for keywords, bbox, label in _REGION_MAP:
        if any(k in lower for k in keywords):
            return bbox, label
    return BBOX_EUROPE, "Europe"


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

    if intent not in {"REALTIME", "KNOWLEDGE", "HYBRID", "ANALYTICS", "ANOMALY", "OUT_OF_SCOPE"}:
        intent = "KNOWLEDGE"

    return {"intent": intent}


async def decline_node(state: AgentState) -> dict:
    """Static graceful-decline response for OUT_OF_SCOPE intents — no LLM call."""
    msg = (
        "**That's outside what I can answer.**\n\n"
        "Aether has access to live flight positions, EU aviation regulations (EU 261 + Eurocontrol "
        "glossary), traffic analytics, and anomaly detection — but **no booking system, ticket prices, "
        "weather feeds, baggage tracking, or per-flight schedule data**.\n\n"
        "**Things I can answer right now:**\n"
        "- How many flights are over [Europe / France / Germany / UK / Italy / Spain] right now\n"
        "- What are the fastest or highest aircraft currently airborne\n"
        "- EU 261 passenger rights (delays, cancellations, denied boarding)\n"
        "- Definitions: squawk codes, ETOPS, IFR/VFR, ATC slots, etc.\n"
        "- Traffic statistics (averages, top countries, distributions)\n"
        "- Anomaly detection on live flight patterns\n\n"
        "Rephrase your question around one of these and I'll have a real answer."
    )
    return {"messages": [AIMessage(content=msg)]}


async def live_tool_node(state: AgentState) -> dict:
    msg = str(state["messages"][-1].content)
    bbox, region = _region_from_message(msg)
    airline_info = _airline_from_message(msg)

    client = OpenSkyClient()
    try:
        flights = await client.get_flights(bbox)
    finally:
        await client.close()

    if airline_info:
        icao3, airline_name = airline_info
        filtered = [f for f in flights if (f.callsign or "").upper().startswith(icao3)]
        airborne = [f for f in filtered if not f.on_ground]
        on_ground = len(filtered) - len(airborne)
        scope = f"{airline_name} flights over {region}"
        total_note = f" (out of {len(flights):,} total aircraft tracked in region)"
    else:
        filtered = flights
        airborne = [f for f in filtered if not f.on_ground]
        on_ground = len(filtered) - len(airborne)
        scope = f"flights over {region}"
        total_note = f" (total tracked: {len(flights):,})"

    top5 = sorted(
        [f for f in airborne if f.velocity],
        key=lambda f: f.velocity,  # type: ignore[arg-type]
        reverse=True,
    )[:5]

    lines = [
        f"**Live {scope}:** {len(airborne)} airborne, {on_ground} on ground{total_note}",
    ]
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
    bbox, region = _region_from_message(str(state["messages"][-1].content))
    client = OpenSkyClient()
    try:
        flights = await client.get_flights(bbox)
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
        f"**Traffic analytics — {region} (live snapshot):**",
        f"- Total aircraft tracked: {len(flights)}",
        f"- Airborne: {len(airborne)} ({len(airborne)/max(len(flights),1)*100:.1f}%)",
        f"- Average speed: {avg_speed:.0f} km/h",
        f"- Average altitude: {avg_alt:.0f} m",
        f"- Top countries: {', '.join(f'{c} ({n})' for c, n in top5)}",
    ]

    return {"tool_results": ["\n".join(lines)]}


async def anomaly_tool_node(state: AgentState) -> dict:
    bbox, region = _region_from_message(str(state["messages"][-1].content))
    client = OpenSkyClient()
    try:
        flights = await client.get_flights(bbox)
    finally:
        await client.close()

    anomalies = detect(flights, top_k=10)
    if not anomalies:
        return {"tool_results": ["Anomaly model not trained yet or no data available."]}

    lines = [f"**Top {len(anomalies)} unusual flights detected over {region} (live anomaly detection):**"]
    for a in anomalies:
        lines.append(
            f"- {a['callsign']} ({a['country']}) — unusual pattern: "
            f"{a['velocity_kmh']} km/h, alt {a['altitude_m']}m, "
            f"vertical rate {a['vertical_rate']} m/s (anomaly score: {a['anomaly_score']})"
        )

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
