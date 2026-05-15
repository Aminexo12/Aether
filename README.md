# Aether

AI-powered agent for real-time aviation data analysis.

## What it does

Aether answers questions about live and historical flight data using a LangGraph agent backed by Claude. It combines:

- **Live flight tracking** via OpenSky Network (positions, speeds, altitudes)
- **Flight & airline data** via AviationStack (routes, schedules, airlines, airports)
- **RAG knowledge base** for aviation domain knowledge (Qdrant vector DB)
- **Anomaly detection** on flight patterns (scikit-learn Isolation Forest)
- **Streamlit dashboard** with real-time map (pydeck) and analytics (Plotly)

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + uvicorn |
| Agent | LangGraph + Claude (Anthropic) |
| Vector DB | Qdrant |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Data sources | OpenSky Network, AviationStack |
| Frontend | Streamlit + pydeck + Plotly |
| ML | scikit-learn Isolation Forest |
| Package manager | uv |

## Getting started

**Prerequisites:** Python 3.11+, Docker, [uv](https://docs.astral.sh/uv/)

```bash
# Clone and install
git clone https://github.com/Aminexo12/Aether.git
cd Aether
uv sync --group dev

# Configure environment
cp .env.example .env
# Fill in your API keys (see Environment variables below)

# Run locally
uv run uvicorn app.main:app --reload

# Or with Docker
docker compose up
```

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |
| `OPENSKY_CLIENT_ID` | OAuth2 client ID from [opensky-network.org](https://opensky-network.org) |
| `OPENSKY_CLIENT_SECRET` | OAuth2 client secret |
| `AVIATIONSTACK_API_KEY` | From [aviationstack.com](https://aviationstack.com) (100 req/month free) |
| `QDRANT_URL` | Defaults to `http://localhost:6333` |
| `LANGSMITH_API_KEY` | Optional — agent observability via LangSmith |

## Project structure

```
app/
  main.py          # FastAPI entrypoint
  config.py        # pydantic-settings (reads .env)
  api/             # Route handlers: chat, flights, analytics
  agents/          # LangGraph graph, nodes, prompts
  data/            # API clients: opensky, aviationstack, models
  rag/             # Vector pipeline: ingest, retrieve
  ml/              # Anomaly detection
  utils/           # Cache, logging
frontend/          # Streamlit app
tests/             # pytest test suite
```

## Agent architecture

```
START → Classifier → [RAG | Live data | Anomaly | Analytics] → Synthesizer → END
```

The classifier (Claude Haiku) tags each query as `REALTIME`, `KNOWLEDGE`, `HYBRID`, or `ANALYTICS` and routes it to the appropriate tool.

## Development

```bash
uv run pytest tests/ -v      # Run tests
uv run ruff check .          # Lint
```

## License

MIT
