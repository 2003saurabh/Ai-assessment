import json
import logging
import os
from pathlib import Path
from typing import List

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings

logger = logging.getLogger(__name__)


class BedrockEmbeddings:
    """Embeddings using Bedrock Titan."""

    def __init__(self):
        from app.services.aws_session import get_aws_session

        session = get_aws_session()
        self.client = session.client("bedrock-runtime")
        self.model_id = "amazon.titan-embed-text-v2:0"

    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        body = json.dumps({"inputText": text})
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]


class VectorStoreService:
    def __init__(self):
        self.embeddings = BedrockEmbeddings()
        self.database_url = settings.DATABASE_URL
        self._initialize()

    def _get_connection(self):
        return psycopg2.connect(self.database_url)

    def _initialize(self):
        """Ensure pgvector extension and table exist, build index if empty."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create document chunks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        source TEXT NOT NULL,
                        embedding vector(1024)
                    )
                """)

                # Create HNSW index for fast similarity search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                    ON document_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)

                conn.commit()

                # Check if we need to build the index
                cur.execute("SELECT COUNT(*) FROM document_chunks")
                count = cur.fetchone()[0]

                if count == 0:
                    logger.info("No document chunks found. Building vector index...")
                    self._build_index(conn)
                else:
                    logger.info(f"Vector store ready with {count} chunks.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize vector store: {e}")
            raise
        finally:
            conn.close()

    def _build_index(self, conn):
        """Load documents, chunk them, embed, and store in pgvector."""
        docs_path = Path(settings.DOCUMENTS_PATH)

        if not docs_path.exists():
            raise FileNotFoundError(f"Documents directory not found: {docs_path}")

        # Load and chunk documents
        chunks = []
        for md_file in docs_path.glob("**/*.md"):
            content = md_file.read_text(encoding="utf-8")
            file_chunks = self._split_text(content)
            source = md_file.name
            for chunk in file_chunks:
                chunks.append({"content": chunk, "source": source})

        logger.info(f"Embedding {len(chunks)} chunks from {len(list(docs_path.glob('**/*.md')))} documents...")

        # Embed and insert
        with conn.cursor() as cur:
            for chunk_data in chunks:
                embedding = self.embeddings.embed(chunk_data["content"])
                cur.execute(
                    """
                    INSERT INTO document_chunks (content, source, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (chunk_data["content"], chunk_data["source"], str(embedding)),
                )
            conn.commit()

        logger.info(f"Vector index built with {len(chunks)} chunks.")

    def _split_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        # Split by headers first, then by size
        separators = ["\n## ", "\n### ", "\n\n", "\n"]
        chunks = []
        current_parts = [text]

        for sep in separators:
            new_parts = []
            for part in current_parts:
                if len(part) <= chunk_size:
                    new_parts.append(part)
                else:
                    splits = part.split(sep)
                    for i, split in enumerate(splits):
                        if i > 0:
                            split = sep.strip() + " " + split
                        new_parts.append(split)
            current_parts = new_parts

        # Merge small chunks and split large ones
        result = []
        buffer = ""

        for part in current_parts:
            if len(buffer) + len(part) <= chunk_size:
                buffer += part
            else:
                if buffer:
                    result.append(buffer.strip())
                if len(part) > chunk_size:
                    # Force split long parts
                    for i in range(0, len(part), chunk_size - overlap):
                        result.append(part[i:i + chunk_size].strip())
                else:
                    buffer = part
        if buffer.strip():
            result.append(buffer.strip())

        return [r for r in result if len(r) > 20]  # Filter out tiny fragments

    def search(self, query: str, k: int = 4) -> list[dict]:
        """Search for relevant documents using cosine similarity."""
        query_embedding = self.embeddings.embed(query)

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT content, source,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM document_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (str(query_embedding), str(query_embedding), k),
                )
                rows = cur.fetchall()

                return [
                    {
                        "content": row["content"],
                        "source": row["source"],
                        "score": float(row["similarity"]),
                    }
                    for row in rows
                ]
        finally:
            conn.close()


# Singleton instance
_vector_store_service = None


def get_vector_store() -> VectorStoreService:
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
