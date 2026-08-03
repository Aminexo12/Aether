# Deploying Aether (free tier)

One Render web service serves **both** the API (`/api/*`) and the built React
frontend (everything else). The vector store lives on **Qdrant Cloud** (free
tier), so there is no second service to pay for. Total cost: **0 €**.

```
Render (free web service, Docker)         Qdrant Cloud (free 1GB cluster)
  /api/*  → FastAPI agent + data      ─▶     RAG vectors (flight_docs)
  /*      → React SPA (in the image)
```

## Prerequisites

- A [Render](https://render.com) account and a [Qdrant Cloud](https://cloud.qdrant.io) account (both free)
- `ANTHROPIC_API_KEY`, and optionally `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET`
- The RAG source documents locally in `app/rag/documents/` (gitignored → not in the image)

## 1. Create the Qdrant Cloud cluster

1. Qdrant Cloud → **Create Cluster** → Free tier.
2. Copy the **cluster URL** (e.g. `https://xyz.cloud.qdrant.io:6333`) and create an **API key**.

## 2. Ingest the RAG documents (one-time, from your machine)

Qdrant starts empty. Point the ingest script at your cloud cluster and run it once:

```bash
QDRANT_URL="https://xyz.cloud.qdrant.io:6333" \
QDRANT_API_KEY="<your-qdrant-cloud-key>" \
  uv run python scripts/ingest_docs.py --path app/rag/documents/ --collection flight_docs
```

Embeddings are computed locally and pushed to the cloud cluster.

## 3. Create the Render web service

1. Render → **New → Blueprint** → connect this GitHub repo.
   Render reads `render.yaml` and provisions a Docker web service on the free plan.
   (Or **New → Web Service → Docker** and point it at the repo manually.)
2. The multi-stage `Dockerfile` builds the React frontend and bakes it into the image.
3. The container listens on Render's injected `$PORT` (see the `CMD` in `Dockerfile`).

## 4. Set environment variables (Render dashboard)

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your key |
| `OPENSKY_CLIENT_ID` | your id (optional — anonymous fallback otherwise) |
| `OPENSKY_CLIENT_SECRET` | your secret (optional) |
| `QDRANT_URL` | your Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | your Qdrant Cloud API key |
| `QDRANT_COLLECTION` | `flight_docs` |

## 5. Deploy & verify

- Render builds and deploys on push to the connected branch.
- Health check: `https://<your-app>.onrender.com/health` → `{"status":"ok"}`
- App: open the root URL — the React SPA loads and calls `/api/*` same-origin.

## Free-tier caveats (be aware)

- **Cold start**: the free web service sleeps after ~15 min idle and takes
  ~50 s to wake on the next request. Fine for a portfolio demo; keep it in mind
  when someone clicks your link cold.
- **Memory (512 MB)**: `KNOWLEDGE` / `HYBRID` queries load a sentence-transformers
  model (torch, ~90 MB weights + runtime). This can approach the free-tier RAM
  limit. Live-flight, analytics, anomaly, and non-RAG chat are lightweight and
  fine. If RAG answers cause restarts, move to a 1 GB+ instance.

## Alternative: Railway

`railway.json` is also included. Railway is simpler (no cold start) but paid
after the one-time $5 trial credit. There you'd run Qdrant as a second service
instead of Qdrant Cloud. See the env-var table above (same keys).

## Local full-stack test

`docker compose up` builds the same image (frontend + backend) and starts a
local Qdrant. The app is served at <http://localhost:8000> — API and SPA together.
