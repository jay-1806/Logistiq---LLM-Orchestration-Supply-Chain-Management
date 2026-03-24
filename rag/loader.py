
import os
import logging
from dataclasses import dataclass
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """
    A single chunk of text with metadata about where it came from.

    metadata.source is CRITICAL for RAG â€” when the agent cites a fact,
    the user needs to know WHERE that fact came from. Traceability.
    """
    content: str
    metadata: dict  # {'source': 'cts_procedures.md', 'chunk_index': 0}


class DocumentLoader:
    """
    Loads documents from a directory and splits them into chunks.

    Supports: .md, .txt files (extendable to PDF, CSV, etc.)
    """

    def __init__(
        self,
        documents_dir: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.documents_dir = documents_dir or settings.documents_dir
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def load_and_chunk(self) -> list[DocumentChunk]:
        """
        Load all supported files and split them into chunks.

        Returns:
            List of DocumentChunks ready for embedding
        """
        all_chunks: list[DocumentChunk] = []

        if not os.path.exists(self.documents_dir):
            logger.warning(f"Documents directory not found: {self.documents_dir}")
            return all_chunks

        # Walk through all files in the documents directory
        for filename in sorted(os.listdir(self.documents_dir)):
            filepath = os.path.join(self.documents_dir, filename)

            if not os.path.isfile(filepath):
                continue

            # Read supported file types
            if filename.endswith((".md", ".txt")):
                text = self._read_text_file(filepath)
            else:
                logger.debug(f"Skipping unsupported file type: {filename}")
                continue

            if not text.strip():
                continue

            # Split into chunks
            chunks = self._split_text(text, source=filename)
            all_chunks.extend(chunks)
            logger.info(f"Loaded {filename}: {len(chunks)} chunks")

        logger.info(f"Total chunks loaded: {len(all_chunks)}")
        return all_chunks

    def _read_text_file(self, filepath: str) -> str:
        """Read a text/markdown file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def _split_text(self, text: str, source: str) -> list[DocumentChunk]:
        """
        Split text into overlapping chunks.

        This is a simplified version of LangChain's RecursiveCharacterTextSplitter.
        We implement it ourselves so you understand HOW it works.

        ALGORITHM:
        1. Start at position 0
        2. Take chunk_size characters
        3. Try to break at the last paragraph/sentence boundary within the chunk
        4. Move forward by (chunk_size - overlap) characters
        5. Repeat until end of text

        The OVERLAP means consecutive chunks share some text. This is important
        because if a key sentence spans a chunk boundary, it appears in both chunks.
        """
        chunks = []
        # Split by paragraphs first (preserves structure)
        paragraphs = text.split("\n\n")

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # If adding this paragraph would exceed chunk_size, save current chunk
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(DocumentChunk(
                    content=current_chunk.strip(),
                    metadata={"source": source, "chunk_index": chunk_index}
                ))
                chunk_index += 1

                # Keep overlap: take the last `chunk_overlap` chars of current chunk
                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    current_chunk = current_chunk[-self.chunk_overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                metadata={"source": source, "chunk_index": chunk_index}
            ))

        return chunks

