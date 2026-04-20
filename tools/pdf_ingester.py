import uuid

from qdrant_client import QdrantClient, models

from tools.data_loader import load_and_chunk_pdf, embed_texts, embed_sparse

qdrant_client = QdrantClient(url="http://localhost:6333")

RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"


def ensure_resume_hybrid_collection() -> None:
    collections = qdrant_client.get_collections().collections
    names = {c.name for c in collections}

    if RESUME_COLLECTION_HYBRID in names:
        return

    qdrant_client.create_collection(
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
    
    source_id = source_id or pdf_path

    ensure_resume_hybrid_collection()

    chunks = load_and_chunk_pdf(pdf_path)
    dense_vecs = embed_texts(chunks)

    points: list[models.PointStruct] = []

    for i, chunk in enumerate(chunks):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}"))

        sparse_indices, sparse_values = embed_sparse(chunk)

        payload = {
            "source": source_id,
            "source_id": source_id,
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

    qdrant_client.upsert(
        collection_name=RESUME_COLLECTION_HYBRID,
        points=points,
    )

    return {
        "ingested": len(chunks),
        "collection": RESUME_COLLECTION_HYBRID,
        "source_id": source_id,
    }