import uuid
import os
from qdrant_client import QdrantClient, models
import re
from tools.data_loader import load_and_chunk_pdf, embed_texts, get_sparse_model


RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"


# =========================================================
# LAZY QDRANT CLIENT (IMPORTANT FIX)
# =========================================================
_qdrant_client = None

import os

def extract_candidate_name(filename: str | None = None) -> str | None:
    if not filename:
        return None

    name = os.path.splitext(filename)[0]  # remove .pdf

    # remove resume noise
    name = re.sub(r"(resume|cv|curriculum|vitae)", "", name, flags=re.I)

    # replace underscores with spaces
    name = name.replace("_", " ")

    # clean extra spaces + symbols
    name = re.sub(r"[^A-Za-z ]", "", name)
    name = " ".join(name.split()).strip().lower()

    return name if name else None

def get_qdrant():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

    return _qdrant_client


def ensure_resume_hybrid_collection():
    client = get_qdrant()

    existing = {c.name for c in client.get_collections().collections}

    if RESUME_COLLECTION_HYBRID in existing:
        return  # ❌ DO NOT TOUCH EXISTING SCHEMA

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


def normalize_resume_filename(filename: str) -> str:
    return filename.strip().lower().replace(" ", "_")


def ingest_pdf_hybrid(pdf_path: str, source_id: str | None = None) -> dict:
    client = get_qdrant()
    ensure_resume_hybrid_collection()

    # Only normalize here (single source of truth)
    source_id = normalize_resume_filename(source_id)

    chunks = load_and_chunk_pdf(pdf_path)
    full_text = "\n".join(chunks)

    candidate_name = extract_candidate_name(source_id)


    dense_vecs = embed_texts(chunks)
    sparse_results = list(get_sparse_model().embed(chunks))

    points = []

    for i, chunk in enumerate(chunks):

        if len(dense_vecs[i]) != 3072:
            raise ValueError("Embedding size mismatch")

        sparse = sparse_results[i]

        payload = {
            "source_id": source_id,
            "candidate_name": candidate_name,
            "chunk_index": i,
            "text": chunk,
        }

        points.append(
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                vector={
                    "dense": dense_vecs[i],
                    "sparse": models.SparseVector(
                        indices=list(sparse.indices),
                        values=list(sparse.values),
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
        "candidate_name": candidate_name
    }