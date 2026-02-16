"""RAG manager for document ingestion and retrieval."""

import threading
from pathlib import Path
from typing import List, Dict, Any
from src.rag.document_processor import DocumentProcessor, QuranDocument
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import FAISSVectorStore
from src.observability.logging import logger


class RAGManager:
    """Manages RAG pipeline: ingestion, indexing, and retrieval."""

    def __init__(
        self,
        knowledge_base_dir: Path,
        index_dir: Path,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.document_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = FAISSVectorStore(
            embedding_service=self.embedding_service,
            dimension=768  # text-embedding-005 dimension
        )

        self.index_path = self.index_dir / "faiss_index.bin"
        self.docs_path = self.index_dir / "documents.pkl"
        self.is_ready = False
        self.ingestion_lock = threading.Lock()

        logger.info(
            "Initialized RAG Manager",
            knowledge_base_dir=str(self.knowledge_base_dir),
            index_dir=str(self.index_dir)
        )

    def ingest_documents(self) -> None:
        """Process and index all PDFs in knowledge base directory."""
        with self.ingestion_lock:
            try:
                logger.info("Starting document ingestion")

                # Find all PDF files
                pdf_files = list(self.knowledge_base_dir.glob("*.pdf"))

                if not pdf_files:
                    logger.warning(
                        "No PDF files found in knowledge base",
                        directory=str(self.knowledge_base_dir)
                    )
                    return

                logger.info(
                    "Found PDF files for ingestion",
                    num_files=len(pdf_files),
                    files=[f.name for f in pdf_files]
                )

                # Process each PDF
                all_documents = []
                for pdf_file in pdf_files:
                    logger.info("Processing PDF", file=pdf_file.name)
                    documents = self.document_processor.process_pdf(pdf_file)
                    all_documents.extend(documents)

                # Add to vector store
                if all_documents:
                    self.vector_store.add_documents(all_documents)

                    # Save index
                    self.vector_store.save(self.index_path, self.docs_path)

                    self.is_ready = True

                    logger.info(
                        "Document ingestion completed",
                        total_documents=len(all_documents),
                        num_pdfs=len(pdf_files)
                    )
                else:
                    logger.warning("No documents extracted from PDFs")

            except Exception as e:
                logger.error(
                    "Document ingestion failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

    def load_index(self) -> bool:
        """Load existing index from disk."""
        try:
            if self.index_path.exists() and self.docs_path.exists():
                logger.info("Loading existing vector store index")
                self.vector_store.load(self.index_path, self.docs_path)
                self.is_ready = True
                logger.info(
                    "Successfully loaded vector store",
                    num_documents=len(self.vector_store.documents)
                )
                return True
            else:
                logger.info("No existing index found")
                return False

        except Exception as e:
            logger.error(
                "Failed to load index",
                error=str(e)
            )
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query.

        Returns:
            List of dictionaries with document text, metadata, and scores
        """
        if not self.is_ready:
            logger.warning("RAG system not ready, attempting to load index")
            if not self.load_index():
                logger.error("RAG system not initialized")
                return []

        results = self.vector_store.search(query, top_k=top_k)

        # Format results
        formatted_results = []
        for doc, distance in results:
            formatted_results.append({
                "text": doc.text,
                "citation": doc.citation,
                "surah": doc.metadata.get("surah", ""),
                "ayah": doc.metadata.get("ayah", ""),
                "distance": distance,
                "metadata": doc.metadata
            })

        logger.info(
            "Retrieved documents",
            query_preview=query[:100],
            num_results=len(formatted_results)
        )

        return formatted_results

    def ingest_in_background(self) -> threading.Thread:
        """Start document ingestion in a background thread."""
        thread = threading.Thread(target=self.ingest_documents, daemon=True)
        thread.start()
        logger.info("Started background document ingestion")
        return thread
