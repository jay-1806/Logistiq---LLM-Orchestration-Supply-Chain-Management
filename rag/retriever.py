
import logging
from rank_bm25 import BM25Okapi
from rag.vectorstore import VectorStore
from rag.loader import DocumentChunk

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines vector search (semantic) with BM25 (keyword) for best retrieval.

    This is your resume bullet: "hybrid retrieval" â€” here's the implementation.
    """

    def __init__(self, vector_store: VectorStore, chunks: list[DocumentChunk], top_k: int = 5):
        """
        Args:
            vector_store: The vector store for dense (semantic) search
            chunks: The original document chunks (needed for BM25 indexing)
            top_k: Number of results to return
        """
        self.vector_store = vector_store
        self.chunks = chunks
        self.top_k = top_k

        # Build BM25 index from the raw text of chunks
        # BM25 needs tokenized documents â€” we use simple whitespace splitting
        logger.info(f"Building BM25 index from {len(chunks)} chunks...")
        tokenized_corpus = [chunk.content.lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info("BM25 index built.")

    def retrieve(self, query: str) -> list[dict]:
        """
        Run hybrid search: combine vector search + BM25 results.

        Args:
            query: Natural language search query

        Returns:
            Top-K results as list of dicts with 'content', 'source', 'score'
        """
        dense_results = self.vector_store.search(query, top_k=self.top_k * 2)

        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # Get top-K BM25 results
        top_bm25_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[: self.top_k * 2]

        sparse_results = []
        for idx in top_bm25_indices:
            if bm25_scores[idx] > 0:  # Only include results that actually match
                sparse_results.append({
                    "content": self.chunks[idx].content,
                    "source": self.chunks[idx].metadata.get("source", "Unknown"),
                    "score": float(bm25_scores[idx]),  # BM25 score (not normalized)
                })

        fused = self._reciprocal_rank_fusion(dense_results, sparse_results)

        logger.info(
            f"Hybrid retrieval: {len(dense_results)} dense + "
            f"{len(sparse_results)} sparse â†’ {len(fused)} fused results"
        )

        return fused[: self.top_k]

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
        k: int = 60,
    ) -> list[dict]:
        """
        Combine two ranked lists using Reciprocal Rank Fusion.

        The RRF formula: score(d) = Î£ 1/(k + rank_i(d))
        where rank_i is the rank of document d in result list i

        Args:
            dense_results: Results from vector search
            sparse_results: Results from BM25 search
            k: Smoothing constant (standard value is 60)

        Returns:
            Fused and re-ranked results
        """
        # Use content as the key (since we don't have unique IDs here)
        rrf_scores: dict[str, float] = {}
        content_map: dict[str, dict] = {}

        # Score dense results by rank
        for rank, result in enumerate(dense_results):
            key = result["content"][:100]  # Use first 100 chars as key
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank + 1)
            content_map[key] = result

        # Score sparse results by rank
        for rank, result in enumerate(sparse_results):
            key = result["content"][:100]
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in content_map:
                content_map[key] = result

        # Sort by combined RRF score (higher = better)
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        fused_results = []
        for key in sorted_keys:
            result = content_map[key].copy()
            result["score"] = round(rrf_scores[key], 4)
            fused_results.append(result)

        return fused_results

