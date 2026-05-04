
import os
import uuid
import re
from functools import lru_cache
import fitz
from dotenv import load_dotenv
from openai import OpenAI
from fastembed import SparseTextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models


# =========================
# ENV + CLIENT SETUP
# =========================
load_dotenv()

openai_client = OpenAI()
_qdrant_client = None

EMBED_MODEL = "text-embedding-3-large"
RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"


# =========================
# QDRANT SETUP
# =========================
def get_qdrant():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

    return _qdrant_client


def ensure_collection(client):
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if RESUME_COLLECTION_HYBRID not in names:
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
            }
        )


# =========================
# SPARSE MODEL
# =========================
@lru_cache(maxsize=1)
def get_sparse_model():
    return SparseTextEmbedding(model_name="Qdrant/bm25")


# =========================
# TEXT CLEANING
# =========================
def clean_text(text):
    text = re.sub(r'[\u200b\u200c\u200d\uFEFF]', '', text)  # remove invisible chars
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# =========================
# PDF LOADING + CHUNKING
# =========================
def load_and_chunk_pdf(path):
    doc = fitz.open(path)
    all_chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    for page_num, page in enumerate(doc):
        text = clean_text(page.get_text("text"))

        splits = splitter.split_text(text)

        for split in splits:
            all_chunks.append({
                "text": split,
                "page": page_num + 1
            })

    return all_chunks


# =========================
# EMBEDDING (BATCHED)
# =========================
def embed_texts(texts, batch_size=100):
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        response = openai_client.embeddings.create(
            model=EMBED_MODEL,
            input=batch,
        )

        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


# =========================
# HELPERS
# =========================
def normalize_resume_filename(filename: str) -> str:
    return filename.strip().lower().replace(" ", "_")


def extract_candidate_name(filename: str | None = None) -> str | None:
    if not filename:
        return None

    name = os.path.splitext(filename)[0]

    name = re.sub(r"(resume|cv|curriculum|vitae)", "", name, flags=re.I)
    name = name.replace("_", " ")
    name = re.sub(r"[^\w\s]", "", name)  # safer than removing everything
    name = " ".join(name.split()).strip().lower()

    return name if name else None


# =========================
# MAIN INGEST FUNCTION
# =========================
def ingest_pdf_hybrid(pdf_path: str, source_id: str | None = None) -> dict:
    client = get_qdrant()
    ensure_collection(client)

    source_id = normalize_resume_filename(source_id or os.path.basename(pdf_path))
    candidate_name = extract_candidate_name(source_id) or ""

    chunks = load_and_chunk_pdf(pdf_path)

    texts = [c["text"] for c in chunks]

    dense_vecs = embed_texts(texts)
    sparse_results = list(get_sparse_model().embed(texts))

    points = []

    for i, chunk in enumerate(chunks):
        dense = dense_vecs[i]
        sparse = sparse_results[i]

        if len(dense) != 3072:
            raise ValueError("Embedding size mismatch")

        payload = {
            "source_id": source_id,
            "candidate_name": candidate_name,
            "chunk_index": i,
            "page": chunk["page"],
            "text": chunk["text"],
        }

        points.append(
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                vector={
                    "dense": dense,
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
        "ingested": len(points),
        "collection": RESUME_COLLECTION_HYBRID,
        "source_id": source_id,
        "candidate_name": candidate_name
    }


# # =========================
# # RUN TEST
# # =========================
# if __name__ == "__main__":
#     path = r"C:\Users\User\OneDrive\Documents\Wish you have a nice job\MAH QING TONG Resume.pdf"

#     result = ingest_pdf_hybrid(path)

#     print(result)