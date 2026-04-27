from fastapi import FastAPI

from app.api.flights import router as flights_router

app = FastAPI(title="Aether", version="0.1.0")

app.include_router(flights_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
