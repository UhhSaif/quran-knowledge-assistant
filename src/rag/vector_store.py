"""FAISS vector store for similarity search."""

import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any
import numpy as np
import faiss
from src.rag.document_processor import QuranDocument
from src.rag.embeddings import EmbeddingService
from src.observability.logging import logger


class FAISSVectorStore:
    """FAISS-based vector store for semantic search."""

    def __init__(self, embedding_service: EmbeddingService, dimension: int = 768):
        self.embedding_service = embedding_service
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.documents: List[QuranDocument] = []

        logger.info(
            "Initialized FAISS vector store",
            dimension=dimension,
            index_type="IndexFlatL2"
        )

    def add_documents(self, documents: List[QuranDocument]) -> None:
        """Add documents to the vector store."""
        if not documents:
            logger.warning("No documents to add to vector store")
            return

        # Extract texts and generate embeddings
        texts = [doc.text for doc in documents]
        logger.info("Generating embeddings for documents", num_documents=len(texts))

        embeddings = self.embedding_service.embed_batch(texts)

        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Add to FAISS index
        self.index.add(embeddings_array)

        # Store documents
        self.documents.extend(documents)

        logger.info(
            "Added documents to vector store",
            num_documents=len(documents),
            total_documents=len(self.documents),
            index_total=self.index.ntotal
        )

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[QuranDocument, float]]:
        """Search for similar documents.

        Returns:
            List of (document, distance) tuples, sorted by similarity (lower distance = more similar)
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty, cannot perform search")
            return []

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Search FAISS index
        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))

        # Prepare results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append((doc, float(distance)))

        logger.info(
            "Performed vector search",
            query_preview=query[:100],
            top_k=top_k,
            num_results=len(results)
        )

        return results

    def save(self, index_path: Path, docs_path: Path) -> None:
        """Save index and documents to disk."""
        # Save FAISS index
        faiss.write_index(self.index, str(index_path))

        # Save documents
        with open(docs_path, 'wb') as f:
            pickle.dump(self.documents, f)

        logger.info(
            "Saved vector store",
            index_path=str(index_path),
            docs_path=str(docs_path),
            num_documents=len(self.documents)
        )

    def load(self, index_path: Path, docs_path: Path) -> None:
        """Load index and documents from disk."""
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))

        # Load documents
        with open(docs_path, 'rb') as f:
            self.documents = pickle.load(f)

        logger.info(
            "Loaded vector store",
            index_path=str(index_path),
            docs_path=str(docs_path),
            num_documents=len(self.documents),
            index_total=self.index.ntotal
        )

    def is_empty(self) -> bool:
        """Check if vector store has any documents."""
        return self.index.ntotal == 0
