"""Vertex AI embeddings service."""

import os
import time
from typing import List
from google import genai
from google.genai import types
from src.observability.logging import logger


class EmbeddingService:
    """Generates embeddings using Google GenAI embedding models."""

    def __init__(self, model_name: str = "models/gemini-embedding-001"):
        self.model_name = model_name

        # Initialize Google GenAI client
        api_key = os.getenv("GOOGLE_GENAI_API_KEY")
        use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"

        if use_vertexai:
            # Use Vertex AI
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            if not project:
                raise ValueError("GOOGLE_CLOUD_PROJECT must be set when using Vertex AI")

            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location
            )
            logger.info(
                "Initialized Vertex AI embeddings",
                project=project,
                location=location,
                model=model_name
            )
        elif api_key:
            # Use API key
            self.client = genai.Client(api_key=api_key)
            logger.info("Initialized GenAI embeddings with API key", model=model_name)
        else:
            raise ValueError(
                "Either GOOGLE_GENAI_API_KEY or GOOGLE_GENAI_USE_VERTEXAI=true must be set"
            )

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=text
            )

            embedding = result.embeddings[0].values
            logger.debug(
                "Generated embedding",
                text_length=len(text),
                embedding_dim=len(embedding)
            )
            return embedding

        except Exception as e:
            logger.error(
                "Failed to generate embedding",
                text_preview=text[:100],
                error=str(e)
            )
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                # Embed each text in the batch with rate limiting
                batch_embeddings = []
                for j, text in enumerate(batch):
                    embedding = self.embed_text(text)
                    batch_embeddings.append(embedding)

                    # Rate limiting: Free tier allows 100 requests/minute
                    # Add 0.7 second delay to stay under limit (86 requests/min)
                    if j < len(batch) - 1:  # Don't sleep after last item
                        time.sleep(0.7)

                all_embeddings.extend(batch_embeddings)

                logger.info(
                    "Processed embedding batch",
                    batch_num=i // batch_size + 1,
                    batch_size=len(batch),
                    total_processed=len(all_embeddings)
                )

            except Exception as e:
                logger.error(
                    "Failed to process embedding batch",
                    batch_num=i // batch_size + 1,
                    error=str(e)
                )
                raise

        logger.info(
            "Completed batch embedding",
            total_embeddings=len(all_embeddings)
        )

        return all_embeddings
