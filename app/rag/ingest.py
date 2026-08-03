import uuid
from datetime import datetime
from pathlib import Path

import pypdf
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from app.config import settings

_CHUNK_SIZE = 800    # characters (~200 tokens, fits all-MiniLM-L6-v2 window)
_CHUNK_OVERLAP = 100
_VECTOR_DIM = 384    # all-MiniLM-L6-v2 output dimension

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


def _ensure_collection(client: QdrantClient, collection: str) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
        )


def _extract_text_from_pdf(path: Path) -> list[tuple[int, str]]:
    """Returns list of (page_number, text) tuples."""
    reader = pypdf.PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = _clean(text)
        if text.strip():
            pages.append((i + 1, text))
    return pages


def _clean(text: str) -> str:
    import re
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        chunks.append(text[start:end])
        start += _CHUNK_SIZE - _CHUNK_OVERLAP
    return [c for c in chunks if len(c.strip()) > 50]


def ingest_pdf(path: Path, collection: str, doc_type: str = "pdf") -> int:
    client = _get_qdrant()
    _ensure_collection(client, collection)
    model = _get_model()

    pages = _extract_text_from_pdf(path)
    points: list[PointStruct] = []

    for page_num, text in pages:
        for chunk in _chunk(text):
            vector = model.encode(chunk).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk,
                    "source": path.name,
                    "page": page_num,
                    "doc_type": doc_type,
                    "ingested_at": datetime.utcnow().isoformat(),
                },
            ))

    if points:
        client.upsert(collection_name=collection, points=points)

    return len(points)
