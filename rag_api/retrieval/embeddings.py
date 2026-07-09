"""Embedding generation and caching."""
from typing import List
import openai
from django.conf import settings


class EmbeddingService:
    """Generate embeddings using OpenAI."""
    
    def __init__(self):
        """Initialize with OpenAI API key."""
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            input=text,
            model=self.model,
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        response = self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        
        # Sort by index to maintain order
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get dimension of embeddings for this model."""
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072
        if "small" in self.model:
            return 1536
        elif "large" in self.model:
            return 3072
        else:
            return 1536  # default
