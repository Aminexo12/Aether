import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.api.chat import _graph
from app.api.analytics import router as analytics_router
from app.api.flights import router as flights_router
from app.api.chat import router as chat_router

app = FastAPI(title="Aether", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights_router)
app.include_router(chat_router)
app.include_router(analytics_router)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest):
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

            if kind == "on_chain_end" and event.get("name") == "classify":
                output = event.get("data", {}).get("output") or {}
                intent = output.get("intent", "")
                if intent:
                    yield f"data: {json.dumps({'type': 'intent', 'value': intent})}\n\n"

            if kind == "on_chat_model_stream" and meta.get("langgraph_node") == "synthesize":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/")
def root():
    return {
        "name": "Aether API",
        "version": app.version,
        "docs": "/docs",
        "endpoints": [
            "GET  /health",
            "GET  /flights/live",
            "GET  /flights/airports/{iata_code}",
            "GET  /flights/airlines/{iata_code}",
            "POST /chat/",
            "POST /chat/stream",
            "GET  /analytics/overview",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
