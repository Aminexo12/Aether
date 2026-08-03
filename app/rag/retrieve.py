from dataclasses import dataclass

from qdrant_client import QdrantClient

from app.config import settings
from app.rag.ingest import _get_model


@dataclass
class SearchResult:
    text: str
    source: str
    page: int
    score: float


def search_docs(query: str, collection: str, top_k: int = 5) -> list[SearchResult]:
    model = _get_model()
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)

    vector = model.encode(query).tolist()
    response = client.query_points(collection_name=collection, query=vector, limit=top_k)

    return [
        SearchResult(
            text=hit.payload["text"],
            source=hit.payload["source"],
            page=hit.payload["page"],
            score=hit.score,
        )
        for hit in response.points
    ]
