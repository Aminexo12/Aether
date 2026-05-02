from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.flights import router as flights_router

app = FastAPI(title="Aether", version="0.1.0")

app.include_router(flights_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
