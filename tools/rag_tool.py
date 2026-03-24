
import logging
from typing import Any
from pydantic import BaseModel, Field
from tools.base import BaseTool
from agent.schemas import UserRole

logger = logging.getLogger(__name__)


class RAGTool(BaseTool):
    """
    Searches internal documents using vector similarity and keyword matching.

    This is the tool the planner uses when the question is about policies,
    procedures, or any unstructured text knowledge.
    """

    name = "doc_search"
    description = (
        "Search internal documents (SOPs, policies, manuals) for relevant information. "
        "Use this for questions about procedures, policies, quality standards, "
        "SLA rules, or any knowledge that isn't in the database tables. "
        "Arguments: query (str) - Natural language search query describing what you need."
    )
    required_role = UserRole.VIEWER  # Everyone can search documents

    class Args(BaseModel):
        query: str = Field(min_length=1, description="Natural language retrieval query")

    args_model = Args

    def __init__(self, retriever=None):
        """
        Args:
            retriever: A retriever object from the RAG pipeline.
                      Injected at startup â€” this tool doesn't build the pipeline itself.
        """
        self.retriever = retriever

    def set_retriever(self, retriever):
        """Set the retriever after initialization (allows lazy setup)."""
        self.retriever = retriever

    def execute(self, query: str = "", **kwargs) -> Any:
        """
        Search documents and return relevant chunks.

        Args:
            query: What to search for (natural language)

        Returns:
            Formatted string with the top matching document chunks + sources
        """
        if not query:
            return "Error: No search query provided."

        if self.retriever is None:
            return "Error: Document retriever not initialized. Run the RAG pipeline setup first."

        logger.info(f"Searching documents for: {query}")

        try:
            # Get relevant chunks from the retriever
            results = self.retriever.retrieve(query)

            if not results:
                return "No relevant documents found for this query."

            # Format results with sources for transparency
            formatted = []
            for i, result in enumerate(results, 1):
                source = result.get("source", "Unknown")
                content = result.get("content", "")
                score = result.get("score", 0.0)
                formatted.append(
                    f"--- Document Chunk {i} (Source: {source}, Relevance: {score:.2f}) ---\n"
                    f"{content}"
                )

            output = "\n\n".join(formatted)
            logger.info(f"Found {len(results)} relevant chunks")
            return output

        except Exception as e:
            error_msg = f"Document search error: {str(e)}"
            logger.error(error_msg)
            return error_msg

