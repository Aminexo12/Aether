import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agents.graph import build_graph

router = APIRouter(prefix="/chat", tags=["chat"])

_graph = build_graph()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    answer: str


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """Synchronous endpoint — full response as JSON. Useful for testing in Swagger."""
    result = await _graph.ainvoke({
        "messages": [HumanMessage(content=body.message)],
        "intent": "",
        "tool_results": [],
    })
    return ChatResponse(
        intent=result["intent"],
        answer=result["messages"][-1].content,
    )


@router.post("/stream")
async def chat_stream(body: ChatRequest):
    """SSE streaming endpoint — emits tokens as they arrive from the synthesizer.

    Event types:
      {"type": "intent",  "value": "REALTIME"}   — emitted once after classification
      {"type": "token",   "content": "..."}       — one per LLM token from synthesizer
      {"type": "done"}                             — stream finished
    """
    async def event_stream():
        async for event in _graph.astream_events(
            {
                "messages": [HumanMessage(content=body.message)],
                "intent": "",
                "tool_results": [],
            },
            version="v2",
        ):
            kind = event["event"]
            meta = event.get("metadata", {})

            # Emit intent once the classifier node completes
            if kind == "on_chain_end" and event.get("name") == "classify":
                output = event.get("data", {}).get("output") or {}
                intent = output.get("intent", "")
                if intent:
                    yield f"data: {json.dumps({'type': 'intent', 'value': intent})}\n\n"

            # Stream tokens from the synthesizer LLM only
            if kind == "on_chat_model_stream" and meta.get("langgraph_node") == "synthesize":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
