import os
from functools import lru_cache
from dotenv import load_dotenv
from openai import OpenAI

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models


# =========================
# ENV + CLIENT
# =========================
load_dotenv()

openai_client = OpenAI()
_qdrant_client = None

EMBED_MODEL = "text-embedding-3-large"
RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"


# =========================
# QDRANT CLIENT
# =========================
def get_qdrant():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

    return _qdrant_client


# =========================
# EMBEDDINGS
# =========================
def embed_dense(text: str):
    return openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=[text]
    ).data[0].embedding


@lru_cache(maxsize=1)
def get_sparse_model():
    return SparseTextEmbedding(model_name="Qdrant/bm25")


def embed_sparse(text: str):
    result = list(get_sparse_model().embed([text]))[0]
    return list(result.indices), list(result.values)


# =========================
# SIMPLE RERANK (by score)
# =========================
def rerank_results(query, search_results, top_k):
    payloads = search_results["payloads"]
    scores = search_results["scores"]

    combined = list(zip(payloads, scores))
    combined.sort(key=lambda x: x[1], reverse=True)

    return [item[0] for item in combined[:top_k]]


# =========================
# SEARCH FUNCTION (FIXED)
# =========================
def search_resume_function(
    question: str,
    top_k: int = 5,
    candidate_name: str | None = None
):
    client = get_qdrant()

    # -----------------------------
    # QUERY (DO NOT INJECT NAME)
    # -----------------------------
    query_text = question

    # -----------------------------
    # EMBEDDINGS
    # -----------------------------
    dense_query = embed_dense(query_text)
    sparse_indices, sparse_values = embed_sparse(query_text)

    # -----------------------------
    # FILTER (SAFE)
    # -----------------------------
    query_filter = None

    if candidate_name:
        normalized = candidate_name.strip().lower()

        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="candidate_name",
                    match=models.MatchValue(value=normalized)
                )
            ]
        )

    # -----------------------------
    # HYBRID SEARCH (RRF)
    # -----------------------------
    response = client.query_points(
        collection_name=RESUME_COLLECTION_HYBRID,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=top_k * 5
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
                using="sparse",
                limit=top_k * 5
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k * 5,
        with_payload=True,
        with_vectors=False,
        query_filter=query_filter,
    )

    # -----------------------------
    # PROCESS RESULTS
    # -----------------------------
    payloads = []
    scores = []

    for point in response.points:
        payloads.append(point.payload or {})
        scores.append(float(point.score or 0.0))

    if not payloads:
        return {"chunks": [], "count": 0}

    search_results = {
        "payloads": payloads,
        "scores": scores,
    }

    # -----------------------------
    # RERANK
    # -----------------------------
    final_chunks = rerank_results(query_text, search_results, top_k)

    return {
        "chunks": final_chunks,
        "count": len(final_chunks)
    }


# =========================
# BUILD CONTEXT
# =========================
def build_context(chunks):
    context_parts = []

    for c in chunks:
        context_parts.append(
            f"[Page {c.get('page')}]\n{c.get('text')}"
        )

    return "\n\n".join(context_parts)


# =========================
# ASK QUESTION (RAG)
# =========================
def ask_resume_question(question: str, candidate_name: str | None = None):
    result = search_resume_function(
        question=question,
        top_k=5,
        candidate_name=candidate_name
    )

    if result["count"] == 0:
        return "No relevant information found."

    context = build_context(result["chunks"])

    prompt = f"""
Answer the question ONLY using the context below.
If not found, say "Not found".

Context:
{context}

Question:
{question}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You answer based only on provided context."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# =========================
# DEBUG HELPERS
# =========================
def debug_search(question):
    result = search_resume_function(question, top_k=5)

    print("\n🔍 QUERY:", question)
    print("=" * 50)

    for i, c in enumerate(result["chunks"]):
        print(f"\n--- Result {i+1} ---")
        print(f"Page: {c.get('page')}")
        print(c.get("text"))


# =========================
# TEST RUN
# =========================
if __name__ == "__main__":
    client = get_qdrant()

    # 🔍 Check DB
    print("Collections:", client.get_collections())
    print("Count:", client.count(collection_name=RESUME_COLLECTION_HYBRID))

    # 🔍 Debug retrieval
    debug_search("show me about the ai project that this candidate worked on")

    # 🤖 Ask question
    answer = ask_resume_question(
        "show me about the ai project that this candidate worked on",
        candidate_name="mah qing tong"  # optional
    )

    print("\nANSWER:\n", answer)