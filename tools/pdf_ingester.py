import uuid
import os
from qdrant_client import QdrantClient, models

from tools.data_loader import load_and_chunk_pdf, embed_texts, embed_sparse

RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"


# =========================================================
# LAZY QDRANT CLIENT (IMPORTANT FIX)
# =========================================================
_qdrant_client = None


def get_qdrant():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

    return _qdrant_client


def ensure_resume_hybrid_collection() -> None:
    client = get_qdrant()

    collections = client.get_collections().collections
    names = {c.name for c in collections}

    if RESUME_COLLECTION_HYBRID in names:
        return

    client.create_collection(
        collection_name=RESUME_COLLECTION_HYBRID,
        vectors_config={
            "dense": models.VectorParams(
                size=3072,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams()
        },
    )


def ingest_pdf_hybrid(pdf_path: str, source_id: str | None = None) -> dict:

    client = get_qdrant()

    source_id = source_id or pdf_path

    ensure_resume_hybrid_collection()

    chunks = load_and_chunk_pdf(pdf_path)
    dense_vecs = embed_texts(chunks)

    points = []

    for i, chunk in enumerate(chunks):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}"))

        sparse_indices, sparse_values = embed_sparse(chunk)

        payload = {
            "source": source_id,
            "chunk_index": i,
            "text": chunk,
        }

        points.append(
            models.PointStruct(
                id=point_id,
                vector={
                    "dense": dense_vecs[i],
                    "sparse": models.SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                },
                payload=payload,
            )
        )

    client.upsert(
        collection_name=RESUME_COLLECTION_HYBRID,
        points=points,
    )

    return {
        "ingested": len(chunks),
        "collection": RESUME_COLLECTION_HYBRID,
        "source_id": source_id,
    }