import uuid
from tools.data_loader import embed_texts, ensure_hybrid_collection, embed_sparse
from qdrant_storage.vector_db import QdrantStorage
from qdrant_client import QdrantClient, models
import sys

qdrant_client = QdrantClient(url="http://localhost:6333")


# Max tokens for the searchable embedding text
# Keep small — this is what gets embedded and compared at query time
MAX_EMBED_TOKENS = 300

def make_cache_key(job: dict) -> str:
    return (
        f"{job.get('title', '').lower().strip()}::"
        f"{job.get('company', '').lower().strip()}::"
        f"{job.get('location', '').lower().strip()}::"
        f"{job.get('link', '').strip()}"
    )

def make_job_id(job: dict) -> str:
    """
    Deterministic UUID based on title + company.
    Same job from different searches = same ID = Qdrant overwrites, no duplicates.
    """
    stable_key = (
        f"{job.get('title', '').lower().strip()}:"
        f"{job.get('company', '').lower().strip()}:"
        f"{job.get('location', '').lower().strip()}:"
        f"{job.get('link', '').strip()}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))


def build_embed_text(job: dict) -> str:
    """
    Build a compact, searchable text for embedding.
    Only includes the most semantically useful content — NOT the full JD.
    Target: ~200-300 tokens to save embedding cost.
    """
    title           = job.get("title", "")
    company         = job.get("company", "")
    location        = job.get("location", "")
    matching_skills = job.get("matching_skills", []) or []
    missing_skills  = job.get("missing_skills",  []) or []
    reason          = job.get("reason",          "") or ""
    fit_score       = job.get("fit_score",       0.0) or 0.0

    # Truncate description to first 150 tokens only (company overview)
    description = job.get("job_description") or job.get("brief_summary") or ""
    desc_tokens = description.split()
    short_desc  = " ".join(desc_tokens[:150]) if len(desc_tokens) > 150 else description

    parts = [
        f"Role: {title}",
        f"Company: {company}",
        f"Location: {location}"
    ]


    if matching_skills:
        parts.append(f"Candidate Matches: {', '.join(matching_skills)}")

    if missing_skills:
        parts.append(f"Candidate Missing: {', '.join(missing_skills)}")

    if reason:
        parts.append(f"Fit Summary: {reason}")

    if fit_score:
        parts.append(f"Fit Score: {fit_score}")

    if short_desc:
        parts.append(f"Overview: {short_desc}")

    return "\n".join(parts)




def ingest_jobs_to_qdrant(jobs: list):
    print(f"Starting ingestion for {len(jobs)} jobs", file=sys.stderr)

    ensure_hybrid_collection()

    new_jobs = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        job_id = job.get("job_id") or make_job_id(job)
        new_jobs.append((job, job_id))

    if not new_jobs:
        print("No new jobs to ingest.", file=sys.stderr)
        return

    embed_texts_list = [build_embed_text(job) for job, _ in new_jobs]


    dense_vectors = embed_texts(embed_texts_list)
    sparse_vectors = [embed_sparse(text) for text in embed_texts_list]

    points = []

    for (job, job_id), dense_vector, sparse in zip(new_jobs, dense_vectors, sparse_vectors):

        if not sparse or len(sparse) != 2:
            continue

        sparse_indices, sparse_values = sparse

        try:
            fit_score = float(job.get("fit_score") or 0.0)
        except Exception:
            fit_score = 0.0

        payload = {
            "source_type": "job",
            "source_id": job_id,
            "job_id": job_id,

            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "link": job.get("link", ""),

            "fit_score": fit_score,
            "matching_skills": job.get("matching_skills") or [],
            "missing_skills": job.get("missing_skills") or [],
            "reason": job.get("reason") or "",
            "job_description": job.get("job_description", ""),
        }

        points.append(
            models.PointStruct(
                id=job_id,
                vector={
                    "dense": dense_vector,
                    "sparse": models.SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                },
                payload=payload,
            )
        )


    qdrant_client.upsert(
        collection_name="job_chunks_hybrid",
        points=points,
    )
