from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct


class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="docs", dim=3072):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection

        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids, vectors, payloads):
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector, top_k: int = 5) -> dict:
        """
        Returns:
        {
            "contexts": [str, ...],   # text chunks (for QA mode)
            "sources":  [str, ...],   # unique sources
            "payloads": [dict, ...]   # full payloads (for ranking mode  includes
                                      # fit_score, title, company, matching_skills, etc.)
        }
        """
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k
        ).points

        contexts = []
        sources  = set()
        payloads = []

        for r in results:
            payload = getattr(r, "payload", None) or {}
            text    = payload.get("text", "")
            source  = payload.get("source", "")

            if text:
                contexts.append(text)
            if source:
                sources.add(source)

            payloads.append(payload)   # always keep full payload

        return {
            "contexts": contexts,
            "sources":  list(sources),
            "payloads": payloads,      # full job metadata lives here
        }

    def exists(self, point_id: str) -> bool:
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id]
        )
        return len(results) > 0

    def get_all_points(self, limit: int = 100):
        result, _ = self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        return result

    def delete_collection(self):
        """Deletes the entire collection."""
        self.client.delete_collection(collection_name=self.collection)
        print(f"Collection '{self.collection}' deleted successfully.")

    

