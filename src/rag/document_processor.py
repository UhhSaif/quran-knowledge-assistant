"""Document processing for PDF extraction and chunking."""

import re
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.observability.logging import logger


class QuranDocument:
    """Represents a processed Quran document chunk."""

    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata
        self.surah = metadata.get("surah", "")
        self.ayah = metadata.get("ayah", "")
        self.citation = f"{self.surah}:{self.ayah}" if self.surah and self.ayah else ""

    def __repr__(self) -> str:
        return f"QuranDocument(citation={self.citation}, text_length={len(self.text)})"


class DocumentProcessor:
    """Processes Quran PDFs into semantically chunked documents."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF file."""
        try:
            reader = PdfReader(str(pdf_path))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n".join(text_parts)
            logger.info(
                "Extracted text from PDF",
                pdf_path=str(pdf_path),
                num_pages=len(reader.pages),
                text_length=len(full_text)
            )
            return full_text

        except Exception as e:
            logger.error(
                "Failed to extract text from PDF",
                pdf_path=str(pdf_path),
                error=str(e)
            )
            raise

    def parse_verse_citation(self, text: str) -> Dict[str, str]:
        """Extract Surah and Ayah information from text.

        Looks for patterns like:
        - Surah 2, Verse 255
        - [2:255]
        - Al-Baqarah 2:255
        """
        metadata = {"surah": "", "ayah": ""}

        # Pattern: Surah X, Verse Y or Surah X:Y
        pattern1 = r"Surah\s+(\d+)[,:]?\s*(?:Verse\s+)?(\d+)"
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            metadata["surah"] = match1.group(1)
            metadata["ayah"] = match1.group(2)
            return metadata

        # Pattern: [X:Y]
        pattern2 = r"\[(\d+):(\d+)\]"
        match2 = re.search(pattern2, text)
        if match2:
            metadata["surah"] = match2.group(1)
            metadata["ayah"] = match2.group(2)
            return metadata

        # Pattern: Surah Name X:Y
        pattern3 = r"(?:Surah\s+)?(?:Al-)?[A-Z][a-z-]+\s+(\d+):(\d+)"
        match3 = re.search(pattern3, text)
        if match3:
            metadata["surah"] = match3.group(1)
            metadata["ayah"] = match3.group(2)
            return metadata

        return metadata

    def chunk_text(self, text: str) -> List[QuranDocument]:
        """Split text into semantic chunks with metadata."""
        chunks = self.text_splitter.split_text(text)
        documents = []

        for i, chunk in enumerate(chunks):
            # Try to extract citation from chunk
            metadata = self.parse_verse_citation(chunk)
            metadata["chunk_id"] = i
            metadata["source"] = "quran_pdf"

            doc = QuranDocument(text=chunk, metadata=metadata)
            documents.append(doc)

        logger.info(
            "Created document chunks",
            num_chunks=len(documents),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        return documents

    def process_pdf(self, pdf_path: Path) -> List[QuranDocument]:
        """Complete pipeline: PDF -> text -> chunks."""
        text = self.extract_text_from_pdf(pdf_path)
        documents = self.chunk_text(text)

        logger.info(
            "Completed PDF processing",
            pdf_path=str(pdf_path),
            num_documents=len(documents)
        )

        return documents
