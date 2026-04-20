from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer

from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from qdrant_client.models import Filter, FieldCondition, MatchValue

from qdrant_storage.vector_db import QdrantStorage

# Sparse embedding model for hybrid search

from fastembed import SparseTextEmbedding

load_dotenv()


# -------------------------------------------------------------------
# Clients
# -------------------------------------------------------------------
openai_client = OpenAI()
qdrant_client = QdrantClient(url="http://localhost:6333")

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

DEFAULT_TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MAX_TOKENS = 500

JOB_COLLECTION_DENSE = "job_chunks"
JOB_COLLECTION_HYBRID = "job_chunks_hybrid"
RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"
RESUME_COLLECTION = "pdf_chunks"

# Cross-encoder reranker
# reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2") # version 1 that we make use of 
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2', local_files_only=True)
# Sparse encoder for hybrid search
# You can change model later if needed
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


# -------------------------------------------------------------------
# Chunking
# -------------------------------------------------------------------
def build_hybrid_chunker(
    max_tokens: int = DEFAULT_MAX_TOKENS,
    merge_peers: bool = True,
):
    tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(DEFAULT_TOKENIZER_MODEL)
    )
    return HybridChunker(
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        merge_peers=merge_peers,
    )


def load_and_chunk_pdf(path: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> list[str]:
    converter = DocumentConverter()
    result = converter.convert(source=path)
    doc = result.document

    chunker = build_hybrid_chunker(max_tokens=max_tokens, merge_peers=True)
    chunks = list(chunker.chunk(dl_doc=doc))

    texts: list[str] = []
    for chunk in chunks:
        text = chunker.contextualize(chunk=chunk)
        if text and text.strip():
            texts.append(text)

    return texts


# -------------------------------------------------------------------
# Dense embeddings (OpenAI)
# -------------------------------------------------------------------
def embed_texts(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def embed_dense(text: str) -> list[float]:
    return embed_texts([text])[0]


# -------------------------------------------------------------------
# Sparse embeddings (FastEmbed)
# -------------------------------------------------------------------
def embed_sparse(text: str) -> tuple[list[int], list[float]]:
    """
    Returns sparse vector as (indices, values).
    """
    sparse_result = next(sparse_model.embed([text]))

    # FastEmbed sparse output usually exposes indices and values
    indices = list(sparse_result.indices)
    values = [float(v) for v in sparse_result.values]

    return indices, values


# -------------------------------------------------------------------
# Optional: create hybrid collection
# Run once before ingesting hybrid points
# -------------------------------------------------------------------
def ensure_hybrid_collection() -> None:
    collections = qdrant_client.get_collections().collections
    names = {c.name for c in collections}

    if JOB_COLLECTION_HYBRID in names:
        return

    qdrant_client.create_collection(
        collection_name=JOB_COLLECTION_HYBRID,
        vectors_config={
            "dense": models.VectorParams(
                size=EMBED_DIM,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams()
        },
    )


# -------------------------------------------------------------------
# Semantic-only search (existing style)
# -------------------------------------------------------------------

def search_resume(question: str, top_k: int, candidate_name: str | None = None) -> list[dict]:
    dense_query = embed_dense(question)
    sparse_indices, sparse_values = embed_sparse(question)

    if candidate_name:
        target_source_id = candidate_name + "_resume.pdf" 



    response = qdrant_client.query_points(
        collection_name=RESUME_COLLECTION_HYBRID,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using="dense"
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
                using="sparse"
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
        with_vectors=False,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="source_id",
                    match=models.MatchValue(value=target_source_id)
                )
            ]
        ) if candidate_name else None,
    )

    payloads: list[dict[str, Any]] = []
    scores: list[float] = []

    for point in response.points:
        payload = dict(point.payload or {})
        payloads.append(payload)
        scores.append(float(point.score) if point.score is not None else 0.0)

    search_results = {
        "payloads": payloads,
        "scores": scores,
    }


    result = rerank_results(question, search_results, top_k)
    
    return result

# -------------------------------------------------------------------
# Hybrid search for jobs
# -------------------------------------------------------------------
def hybrid_search_jobs(question: str, top_k: int = 5) -> dict:
    """
    Returns a dict in a shape compatible with rerank_results():
    {
        "payloads": [...],
        "scores": [...]
    }
    """
    dense_query = embed_dense(question)
    sparse_indices, sparse_values = embed_sparse(question)

    response = qdrant_client.query_points(
        collection_name=JOB_COLLECTION_HYBRID,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=max(top_k * 4, 20),
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
                using="sparse",
                limit=max(top_k * 4, 20),
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    payloads: list[dict[str, Any]] = []
    scores: list[float] = []

    for point in response.points:
        payload = dict(point.payload or {})
        payloads.append(payload)
        scores.append(float(point.score) if point.score is not None else 0.0)

    return {
        "payloads": payloads,
        "scores": scores,
    }


def search_jobs_from_qd(question: str, top_k: int) -> dict:
    """
    Main job search entrypoint.
    Uses hybrid search instead of dense-only search.
    """
    return hybrid_search_jobs(question, top_k)


# -------------------------------------------------------------------
# Reranking
# -------------------------------------------------------------------
def rerank_results(question: str, search_results: dict, top_k: int = 3) -> list[dict]:
    payloads = search_results.get("payloads", [])

    if not payloads:
        return []

    texts = [p.get("text", "") for p in payloads]

    pairs = [[question, text] for text in texts]
    scores = reranker.predict(pairs)

    reranked = sorted(      
        zip(scores, payloads),
        key=lambda x: x[0],
        reverse=True,
    )

    results: list[dict[str, Any]] = []          
    for score, payload in reranked[:top_k]:
        results.append({
            "text": payload.get("text", ""),
            "source": payload.get("source") or payload.get("source_id", ""),
            "score": float(score),
            "payload": payload,
        })

    return results
