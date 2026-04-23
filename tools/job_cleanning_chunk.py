# # tools/job_cleanning_chunk.py

# import uuid
# import re
# from tools.data_loader import embed_texts
# from qdrant_storage.vector_db import QdrantStorage
# import sys

# MAX_CHUNK_TOKENS = 500
# OVERLAP_TOKENS   = 50

# # Section header patterns that appear in real job descriptions
# # Each tuple: (section_name, list of possible headers to match)
# SECTION_PATTERNS = [
#     ("overview",          ["Overview:", "WHAT YOU DO", "About the Role", "About This Role"]),
#     ("responsibilities",  ["Responsibilities:", "KEY RESPONSIBILITIES", "THE ROLE:", "Role Description", "What You'll Do"]),
#     ("qualifications",    ["PREFERRED EXPERIENCE", "Qualifications", "Requirements", "What We're Looking For", "Required Skills"]),
# ]


# def simple_tokenizer(text):
#     return text.split()


# def split_text(text, max_tokens=MAX_CHUNK_TOKENS, overlap=OVERLAP_TOKENS):
#     tokens = simple_tokenizer(text)
#     chunks = []
#     start  = 0
#     while start < len(tokens):
#         end = min(start + max_tokens, len(tokens))
#         chunks.append(" ".join(tokens[start:end]))
#         if end == len(tokens):
#             break
#         start = end - overlap
#     return chunks


# def split_job_into_sections(description: str) -> dict:
#     """
#     Splits a raw job description string into named sections.
#     Returns a dict like: {"overview": "...", "responsibilities": "...", "qualifications": "..."}
#     Falls back to putting everything in overview if no headers are found.
#     """
#     # Find all section boundaries
#     boundaries = []  # list of (char_index, section_name, header_str)
#     for section_name, headers in SECTION_PATTERNS:
#         for header in headers:
#             idx = description.find(header)
#             if idx != -1:
#                 boundaries.append((idx, section_name, header))
#                 break  # use first matching header per section

#     if not boundaries:
#         # No recognizable headers — put everything in overview
#         return {"overview": description.strip()}

#     # Sort by position in text
#     boundaries.sort(key=lambda x: x[0])

#     sections = {}
#     for i, (start_idx, section_name, _) in enumerate(boundaries):
#         end_idx = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(description)
#         sections[section_name] = description[start_idx:end_idx].strip()

#     # Everything before the first header becomes overview (if not already captured)
#     first_boundary_idx = boundaries[0][0]
#     if first_boundary_idx > 0 and "overview" not in sections:
#         sections["overview"] = description[:first_boundary_idx].strip()

#     return sections


# def make_chunk_id(job: dict, section: str, chunk_index: int) -> str:
#     """
#     Deterministic UUID based on title + company + section + chunk_index.
#     Same job from different searches = same ID = Qdrant overwrites instead of duplicating.
#     """
#     stable_key = (
#         f"{job.get('title', '').lower().strip()}"
#         f":{job.get('company', '').lower().strip()}"
#         f":{section}"
#         f":{chunk_index}"
#     )
#     return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))


# def chunk_job(job: dict) -> list[dict]:
#     company  = job.get("company")  or "Unknown Company"
#     title    = job.get("title")    or "Unknown Role"
#     location = job.get("location") or "Unknown Location"
#     link     = job.get("link")     or ""
#     job_id   = job.get("job_id")   or str(uuid.uuid4())

#     description = (
#         job.get("job_description")
#         or job.get("brief_summary")
#         or ""
#     )

#     # Enriched fields from ranking / resume matching
#     fit_score       = job.get("fit_score", 0.0) or 0.0
#     matching_skills = job.get("matching_skills", []) or []
#     missing_skills  = job.get("missing_skills", []) or []
#     reason          = job.get("reason", "") or ""
#     required_skills = job.get("required_skills", []) or []
#     employment_type = job.get("employment_type", "") or ""

#     # Only universal metadata goes here
#     base_meta = {
#         "source_type": "job",
#         "source_id": job_id,
#         "job_id": job_id,
#         "title": title,
#         "company": company,
#         "location": location,
#         "link": link,
#         "employment_type": employment_type,
#     }

#     chunks = []

#     # Split description into named sections based on actual headers
#     sections = split_job_into_sections(description)
#     print(f"  Sections found for '{title}': {list(sections.keys())}", file=sys.stderr)

#     section_prefixes = {
#         "overview":         f"Company: {company}\nRole: {title}\nLocation: {location}\n",
#         "responsibilities": f"Company: {company}\nRole: {title}\nResponsibilities:\n",
#         "qualifications":   f"Company: {company}\nRole: {title}\nQualifications:\n",
#         "ranking":          f"Company: {company}\nRole: {title}\nRanking Analysis:\n",
#     }

#     # ---- Normal JD sections ----
#     for section_name, section_text in sections.items():
#         if not section_text.strip():
#             continue

#         prefix = section_prefixes.get(
#             section_name,
#             f"Company: {company}\nRole: {title}\n"
#         )

#         for i, c in enumerate(split_text(section_text)):
#             chunks.append({
#                 **base_meta,
#                 "text": prefix + c,
#                 "section": section_name,
#                 "chunk_index": i,
#                 "_id": make_chunk_id(job, section_name, i),
#             })

#     # ---- Ranking section as its own extra chunk ----
#     if matching_skills or missing_skills or reason or required_skills or fit_score:
#         ranking_text = (
#             f"Fit Score: {fit_score}\n"
#             f"Required Skills: {', '.join(required_skills) if required_skills else 'None'}\n"
#             f"Matching Skills: {', '.join(matching_skills) if matching_skills else 'None'}\n"
#             f"Missing Skills: {', '.join(missing_skills) if missing_skills else 'None'}\n"
#             f"Reason: {reason if reason else 'No reason provided'}"
#         )

#         chunks.append({
#             **base_meta,
#             "text": section_prefixes["ranking"] + ranking_text,
#             "section": "ranking",
#             "chunk_index": 0,
#             "_id": make_chunk_id(job, "ranking", 0),
#         })

#     return chunks


# def ingest_jobs_to_qdrant(jobs: list):
#     print(f"Starting ingestion for {len(jobs)} jobs", file=sys.stderr)

#     storage = QdrantStorage(collection="job_chunks")

#     new_jobs = []
#     skipped  = 0

#     for job in jobs:
#         anchor_id = make_chunk_id(job, "overview", 0)
#         if storage.exists(anchor_id):
#             print(f"  SKIP (already stored): '{job.get('title')}' @ '{job.get('company')}'", file=sys.stderr)
#             skipped += 1
#         else:
#             new_jobs.append(job)

#     print(f"  {skipped} jobs skipped, {len(new_jobs)} new jobs to ingest", file=sys.stderr)

#     if not new_jobs:
#         print("No new jobs to ingest.", file=sys.stderr)
#         return

#     all_chunks = []
#     for job in new_jobs:
#         job_chunks = chunk_job(job)
#         print(f"  '{job.get('title')}' → {len(job_chunks)} chunks", file=sys.stderr)
#         all_chunks.extend(job_chunks)

#     print(f"Total new chunks: {len(all_chunks)}", file=sys.stderr)

#     texts    = [c["text"] for c in all_chunks]
#     vectors  = embed_texts(texts)
#     ids      = [c["_id"] for c in all_chunks]
#     payloads = [{k: v for k, v in c.items() if k != "_id"} for c in all_chunks]

#     print(f"Upserting {len(ids)} vectors to Qdrant...", file=sys.stderr)
#     storage.upsert(ids, vectors, payloads)
#     print("Qdrant upsert complete", file=sys.stderr)
# tools/job_cleanning_chunk.py

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

    print(f"Embedding {len(embed_texts_list)} jobs...", file=sys.stderr)

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

    print(f"Upserting {len(points)} job points...", file=sys.stderr)

    qdrant_client.upsert(
        collection_name="job_chunks_hybrid",
        points=points,
    )

    print("Hybrid Qdrant upsert complete", file=sys.stderr)