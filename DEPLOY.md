# Deploying Aether

Single-service setup: one FastAPI container serves **both** the API (`/api/*`)
and the built React frontend (everything else). A second container runs Qdrant.
No CORS, one public URL.

```
Railway project
├── aether        (this repo, Dockerfile)   → public URL
│     /api/*  → FastAPI agent + data endpoints
│     /*      → React SPA (built into the image)
└── qdrant        (qdrant/qdrant image)      → private, RAG vector store
```

## Prerequisites

- A [Railway](https://railway.app) account (Hobby plan has a free monthly credit)
- API keys: `ANTHROPIC_API_KEY`, and optionally `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET`
- The RAG source documents locally in `app/rag/documents/` (they are gitignored, so not in the image)

## 1. Create the app service

1. Railway → **New Project** → **Deploy from GitHub repo** → select `Aether`.
2. Railway detects the `Dockerfile` and `railway.json` automatically.
   The multi-stage build compiles the React frontend and bakes it into the image.
3. The container binds to Railway's injected `$PORT` (see the `CMD` in `Dockerfile`).

## 2. Add the Qdrant service

1. In the same project → **New** → **Empty Service** (or **Docker Image**).
2. Set the image to `qdrant/qdrant:latest`.
3. Add a **Volume** mounted at `/qdrant/storage` so vectors survive restarts.

## 3. Configure environment variables (on the *aether* service)

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your key |
| `OPENSKY_CLIENT_ID` | your id (optional — anonymous fallback otherwise) |
| `OPENSKY_CLIENT_SECRET` | your secret (optional) |
| `QDRANT_URL` | `http://qdrant.railway.internal:6333` (Railway private network host of the Qdrant service) |
| `QDRANT_COLLECTION` | `flight_docs` |

> The private host is `<service-name>.railway.internal`. Confirm the exact name
> in the Qdrant service's **Settings → Networking → Private Networking**.

## 4. Deploy & verify

- Railway builds and deploys on push to the connected branch.
- Health check: `https://<your-app>.up.railway.app/health` → `{"status":"ok"}`
- App: open the root URL — the React SPA loads and hits `/api/*` same-origin.

## 5. Populate the RAG collection (one-time)

Qdrant starts **empty**, so `KNOWLEDGE` / `HYBRID` queries have no context until
you ingest the documents. Because `app/rag/documents/` is gitignored, ingest from
your local machine against the deployed Qdrant:

1. Qdrant service → **Settings → Networking** → enable a **TCP Proxy** (or public
   domain) on port `6333`. Note the `host:port`.
2. Locally, point ingest at it and run:

   ```bash
   QDRANT_URL="http://<proxy-host>:<proxy-port>" \
     uv run python scripts/ingest_docs.py --path app/rag/documents/ --collection flight_docs
   ```

3. Disable the public TCP proxy again once ingestion completes.

Until this is done, live-flight, analytics, and anomaly features work fully;
only the regulatory-knowledge answers are degraded.

## Local full-stack test (optional)

`docker compose up` builds the same image (frontend + backend) and starts Qdrant.
The app is then served at <http://localhost:8000> — API and SPA together.
