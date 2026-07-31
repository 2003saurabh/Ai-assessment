import os
import json
import numpy as np
from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.embeddings.base import Embeddings

from app.config import settings


class BedrockEmbeddings(Embeddings):
    """Custom embeddings class using Bedrock Titan."""

    def __init__(self):
        from app.services.aws_session import get_aws_session

        session = get_aws_session()
        self.client = session.client("bedrock-runtime")
        self.model_id = "amazon.titan-embed-text-v2:0"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embeddings.append(self._embed(text))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        body = json.dumps({"inputText": text})
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["embedding"]


class VectorStoreService:
    def __init__(self):
        self.embeddings = BedrockEmbeddings()
        self.vector_store = None
        self._initialize()

    def _initialize(self):
        """Load or create the FAISS index."""
        index_path = Path(settings.FAISS_INDEX_PATH)

        if index_path.exists() and (index_path / "index.faiss").exists():
            self.vector_store = FAISS.load_local(
                str(index_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            self._build_index()

    def _build_index(self):
        """Build FAISS index from documents."""
        docs_path = Path(settings.DOCUMENTS_PATH)

        if not docs_path.exists():
            raise FileNotFoundError(
                f"Documents directory not found: {docs_path}"
            )

        # Load all markdown files
        loader = DirectoryLoader(
            str(docs_path),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()

        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "],
        )
        chunks = text_splitter.split_documents(documents)

        # Create FAISS index
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

        # Save index
        index_path = Path(settings.FAISS_INDEX_PATH)
        index_path.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(index_path))

    def search(self, query: str, k: int = 4) -> list[dict]:
        """Search for relevant documents."""
        if not self.vector_store:
            return []

        results = self.vector_store.similarity_search_with_score(query, k=k)

        return [
            {
                "content": doc.page_content,
                "source": os.path.basename(doc.metadata.get("source", "unknown")),
                "score": float(score),
            }
            for doc, score in results
        ]


# Singleton instance
_vector_store_service = None


def get_vector_store() -> VectorStoreService:
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
