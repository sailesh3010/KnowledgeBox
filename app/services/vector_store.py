import numpy as np
from typing import List, Dict, Any, Optional
from app.db.database import db
from app.core.logging import logger


class VectorSearchResult:
    def __init__(
        self,
        chunk_id: str,
        item_id: str,
        source_title: str,
        source_type: str,
        url: Optional[str],
        chunk_index: int,
        content: str,
        similarity_score: float,
    ):
        self.chunk_id = chunk_id
        self.item_id = item_id
        self.source_title = source_title
        self.source_type = source_type
        self.url = url
        self.chunk_index = chunk_index
        self.content = content
        self.similarity_score = similarity_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "item_id": self.item_id,
            "source_title": self.source_title,
            "source_type": self.source_type,
            "url": self.url,
            "chunk_index": self.chunk_index,
            "snippet": self.content,
            "similarity_score": round(float(self.similarity_score), 4),
        }


class SQLiteVectorStore:
    """
    Lightweight, persistent SQLite vector store.
    Stores high-dimensional embeddings and executes fast vectorized cosine similarity
    using NumPy matrix dot product.
    """

    def __init__(self):
        self.db = db

    def search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        min_score: float = 0.05,
    ) -> List[VectorSearchResult]:
        """
        Execute cosine similarity search over all indexed chunks.
        Returns top_k results with similarity >= min_score, sorted descending by score.
        """
        chunks = self.db.get_all_chunks_with_embeddings()
        if not chunks:
            logger.info("Vector search called on empty database.")
            return []

        # Convert query and chunk vectors to NumPy arrays
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 1e-9:
            q_vec = q_vec / q_norm

        embeddings_matrix = np.array([c["embedding"] for c in chunks], dtype=np.float32)

        # Ensure chunk vectors are normalized
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_matrix = embeddings_matrix / norms

        # Cosine similarity via dot product: (N, D) x (D,) -> (N,)
        scores = np.dot(normalized_matrix, q_vec)

        # Collect and filter results
        results: List[VectorSearchResult] = []
        for idx, score in enumerate(scores):
            score_val = float(score)
            if score_val >= min_score:
                c = chunks[idx]
                results.append(VectorSearchResult(
                    chunk_id=c["chunk_id"],
                    item_id=c["item_id"],
                    source_title=c["source_title"],
                    source_type=c["source_type"],
                    url=c["url"],
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    similarity_score=score_val,
                ))

        # Sort descending by similarity score
        results.sort(key=lambda r: r.similarity_score, reverse=True)

        return results[:top_k]


vector_store = SQLiteVectorStore()
