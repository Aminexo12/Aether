# Aether

![CI](https://github.com/Aminexo12/Aether/actions/workflows/ci.yml/badge.svg?branch=develop)

AI-powered agent for real-time aviation data analysis.

## What it does

Aether answers questions about live and historical flight data using a LangGraph agent backed by Claude, and presents it through a real-time 3D web interface. It combines:

- **Live flight tracking** via OpenSky Network (positions, speeds, altitudes, callsigns)
- **Airport & airline data** from bundled OpenFlights static datasets (no third-party key needed)
- **RAG knowledge base** for aviation domain knowledge — Eurocontrol glossary + EU 261/2004 (Qdrant vector DB)
- **Anomaly detection** on flight patterns (scikit-learn Isolation Forest)
- **React 3D frontend** — live map (deck.gl), conversational chat (SSE streaming), and an analytics dashboard (Recharts)

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + uvicorn |
| Agent | LangGraph + Claude (Anthropic) |
| Vector DB | Qdrant |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Data sources | OpenSky Network API + OpenFlights static CSVs |
| Frontend | React + TypeScript + Vite (deck.gl · Recharts · Three.js · GSAP / Framer Motion) |
| ML | scikit-learn Isolation Forest |
| Package manager | uv (backend) · npm (frontend) |

## Getting started

**Prerequisites:** Python 3.11+, Node 18+, Docker (for Qdrant), [uv](https://docs.astral.sh/uv/)

### 1. Backend

```bash
git clone https://github.com/Aminexo12/Aether.git
cd Aether
uv sync --group dev

# Configure environment
cp .env.example .env
# Fill in your keys (see Environment variables below)

# Start Qdrant (RAG vector DB)
docker compose up -d

# Run the API
uv run uvicorn app.main:app --reload
# → http://127.0.0.1:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173  (proxies /api → http://127.0.0.1:8000)
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | From [console.anthropic.com](https://console.anthropic.com) |
| `OPENSKY_CLIENT_ID` | ✅* | OAuth2 client ID from [opensky-network.org](https://opensky-network.org) |
| `OPENSKY_CLIENT_SECRET` | ✅* | OAuth2 client secret |
| `QDRANT_URL` | — | Defaults to `http://localhost:6333` |
| `AVIATIONSTACK_API_KEY` | — | Optional / unused — airport & airline data come from bundled OpenFlights CSVs |
| `LANGSMITH_API_KEY` | — | Optional — agent observability via LangSmith |

\* OpenSky credentials are optional but recommended: without them the app falls back to the anonymous OpenSky API (lower rate limit).

## Project structure

```
app/
  main.py          # FastAPI entrypoint
  config.py        # pydantic-settings (reads .env)
  api/             # Route handlers: chat, flights, analytics
  agents/          # LangGraph graph, nodes, prompts
  data/            # OpenSky client + OpenFlights static data
  rag/             # Vector pipeline: ingest, retrieve
  ml/              # Anomaly detection
  utils/           # Cache, logging
frontend/          # React + TypeScript + Vite single-page app
  src/components/   # Hero, Chat, Map (deck.gl), Analytics, radar scope, ...
tests/             # pytest test suite
eval/              # Eval dataset + runner
```

## Agent architecture

```
START → Classifier → [RAG | Live data | Analytics | Anomaly] → Synthesizer → END
```

The classifier (Claude Haiku) tags each query with one intent and routes it to the matching tool:

| Intent | Tool | Source |
|---|---|---|
| `REALTIME` | live | OpenSky |
| `KNOWLEDGE` | rag | Qdrant |
| `HYBRID` | live + rag | OpenSky + Qdrant |
| `ANALYTICS` | analytics | OpenSky + computed stats |
| `ANOMALY` | anomaly | Isolation Forest |

The synthesizer (Claude) composes the final answer from the tool output. `POST /chat` returns JSON; `POST /chat/stream` streams tokens over SSE.

## Development

```bash
uv run pytest tests/ -v      # Run tests
uv run ruff check .          # Lint
```

## License

MIT
