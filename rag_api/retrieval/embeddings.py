"""Embedding generation and caching."""
from typing import List
import google.generativeai as genai
from django.conf import settings


class EmbeddingService:
    """Generate embeddings using Gemini."""

    # gemini-embedding-001 natively outputs 3072-dim vectors but supports
    # Matryoshka truncation via output_dimensionality - 768 keeps Qdrant
    # storage small while staying within the model's officially supported sizes.
    DIMENSION = 768

    def __init__(self):
        """Initialize with Gemini API key."""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        result = genai.embed_content(
            model=self.model, content=text, output_dimensionality=self.DIMENSION
        )
        return result['embedding']

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        result = genai.embed_content(
            model=self.model, content=texts, output_dimensionality=self.DIMENSION
        )
        return result['embedding']

    def get_embedding_dimension(self) -> int:
        """Get dimension of embeddings for this model."""
        return self.DIMENSION
