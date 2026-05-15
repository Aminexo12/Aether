import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.analytics import router as analytics_router
from app.api.chat import _graph
from app.api.chat import router as chat_router
from app.api.flights import router as flights_router
from app.utils.logging import configure_logging, get_logger

_log = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="Aether", version="0.3.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights_router)
app.include_router(chat_router)
app.include_router(analytics_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - t0) * 1000)
    _log.info("request", method=request.method, path=request.url.path, status=response.status_code, ms=ms)
    return response


class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        if len(v) > 2000:
            raise ValueError("message must be 2000 characters or fewer")
        return v


@app.post("/chat/stream")
@limiter.limit("10/minute")
async def chat_stream(request: Request, body: ChatRequest):
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
