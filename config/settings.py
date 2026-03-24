
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """
    All configuration lives here. Each field maps to an environment variable.
    e.g., groq_api_key â†’ GROQ_API_KEY in .env
    """

    # --- LLM Configuration ---
    groq_api_key: str = Field(
        default="",
        description="Your Groq API key from https://console.groq.com/keys"
    )
    llm_model_name: str = Field(
        default="llama-3.1-8b-instant",
        description="Which Groq-hosted model to use. 'llama-3.1-8b-instant' is fast and low-cost."
    )
    llm_temperature: float = Field(
        default=0.0,
        description="0 = deterministic (same input â†’ same output). "
                    "Higher = more creative/random. For enterprise tools, keep at 0."
    )

    # --- Embedding Configuration ---
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Local embedding model. Runs on your machine, no API key needed. "
                    "384-dimensional vectors, good quality, very fast."
    )

    # --- Data Paths ---
    chroma_persist_dir: str = Field(
        default="./data/chromadb",
        description="Where ChromaDB stores vector indices on disk."
    )
    database_path: str = Field(
        default="./data/supply_chain.db",
        description="SQLite database with supply chain tables."
    )
    documents_dir: str = Field(
        default="./data/documents",
        description="Directory containing documents to ingest into RAG."
    )

    # --- RAG Configuration ---
    chunk_size: int = Field(
        default=512,
        description="How many characters per text chunk. Smaller = more precise retrieval, "
                    "but loses context. Larger = more context, but less precise."
    )
    chunk_overlap: int = Field(
        default=64,
        description="Overlap between chunks so we don't cut sentences in half."
    )
    top_k: int = Field(
        default=5,
        description="Number of chunks to retrieve per query."
    )

    # --- Monitoring ---
    log_level: str = Field(default="INFO")
    mlflow_tracking_uri: str = Field(
        default="./mlruns",
        description="Where MLflow stores experiment data."
    )

    # --- UI / Access Control ---
    role_change_pin: str = Field(
        default="",
        description="Optional PIN used to unlock role switching in the Streamlit sidebar."
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # This means GROQ_API_KEY in .env maps to groq_api_key field
        case_sensitive = False
        # Ignore unrelated env vars (common on hosted platforms like Streamlit Cloud)
        extra = "ignore"


# Create a single global instance â€” import this everywhere
# Usage: from config.settings import settings
settings = Settings()

