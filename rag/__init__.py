
import logging
from typing import Optional
import chromadb
from sentence_transformers import SentenceTransformer
from rag.loader import DocumentChunk
from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages embedding generation and vector storage using ChromaDB.

    Two main operations:
    1. add_chunks() â€” embed documents and store them (done once at setup)
    2. search() â€” embed a query and find similar stored chunks (done per query)
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        embedding_model_name: str | None = None,
        collection_name: str = "supply_chain_docs",
    ):
        """
        Args:
            persist_dir: Where to save the vector database on disk
            embedding_model_name: Which sentence-transformers model to use
            collection_name: Name of the ChromaDB collection (like a "table")
        """
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name

        # --- Load the embedding model ---
        # This runs LOCALLY â€” no API key, no cost, no rate limits
        # all-MiniLM-L6-v2 creates 384-dimensional vectors
        # It's small (80MB) but surprisingly good for document retrieval
        model_name = embedding_model_name or settings.embedding_model_name
        logger.info(f"Loading embedding model: {model_name}")
        self.embed_model = SentenceTransformer(model_name)

        # --- Initialize ChromaDB ---
        # PersistentClient = data survives between restarts
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        logger.info(
            f"Vector store initialized. Collection '{collection_name}' "
            f"has {self.collection.count()} documents."
        )

    def add_chunks(self, chunks: list[DocumentChunk]):
        """
        Embed chunks and add them to the vector database.

        This is called ONCE during setup (or when new documents are added).
        After this, the chunks are searchable by meaning.

        Args:
            chunks: List of DocumentChunks from the loader
        """
        if not chunks:
            logger.warning("No chunks to add.")
            return

        # Prepare data for ChromaDB
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [f"{chunk.metadata['source']}_{chunk.metadata['chunk_index']}" for chunk in chunks]

        # Generate embeddings for all chunks at once (batch processing is faster)
        logger.info(f"Embedding {len(chunks)} chunks...")
        embeddings = self.embed_model.encode(documents, show_progress_bar=True)

        # Add to ChromaDB (upsert = update if exists, insert if new)
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings.tolist(),
        )

        logger.info(f"Added {len(chunks)} chunks to vector store.")

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Search for chunks most similar to the query.

        Args:
            query: The search query (natural language)
            top_k: How many results to return

        Returns:
            List of dicts with 'content', 'source', 'score' keys
        """
        top_k = top_k or settings.top_k

        if self.collection.count() == 0:
            logger.warning("Vector store is empty â€” no documents to search.")
            return []

        # Embed the query using the same model
        query_embedding = self.embed_model.encode([query])[0]

        # Search ChromaDB â€” it finds the top-K most similar vectors
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        for i in range(len(results["documents"][0])):
            # ChromaDB returns distances; for cosine, smaller = more similar
            # Convert to a 0-1 score where 1 = most similar
            distance = results["distances"][0][i]
            score = 1 - distance  # cosine distance â†’ cosine similarity

            formatted.append({
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i].get("source", "Unknown"),
                "score": round(score, 4),
            })

        return formatted

    def reset(self):
        """Delete all documents from the collection (for re-indexing)."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Vector store reset.")

