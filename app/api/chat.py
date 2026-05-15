from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, field_validator

from app.agents.graph import build_graph

router = APIRouter(prefix="/chat", tags=["chat"])

_graph = build_graph()


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


