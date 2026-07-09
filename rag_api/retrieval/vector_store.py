"""Qdrant vector store integration."""
from typing import List, Dict, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from django.conf import settings


class VectorStore:
    """Manages vector embeddings in Qdrant."""
    
    def __init__(self, collection_name: str = "documents", vector_size: int = 1536):
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of Qdrant collection
            vector_size: Dimension of embeddings (1536 for text-embedding-3-small)
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
    
    def add_vector(self, embedding: List[float], metadata: Dict, 
                   point_id: str = None) -> str:
        """
        Add a single vector with metadata.
        
        Returns:
            Point ID
        """
        if point_id is None:
            point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=metadata,
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        
        return point_id
    
    def add_vectors(self, embeddings: List[List[float]], 
                   metadatas: List[Dict]) -> List[str]:
        """
        Add multiple vectors with metadata.
        
        Returns:
            List of point IDs
        """
        points = []
        point_ids = []
        
        for embedding, metadata in zip(embeddings, metadatas):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata,
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        
        return point_ids
    
    def search(self, embedding: List[float], top_k: int = 10,
               filter_dict: Dict = None) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar vectors.
        
        Returns:
            List of (point_id, similarity_score, metadata) tuples
        """
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=top_k,
            query_filter=filter_dict,
        )
        
        return [
            (str(result.id), result.score, result.payload)
            for result in results
        ]
    
    def delete_vector(self, point_id: str) -> None:
        """Delete a vector by ID."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[point_id],
        )
    
    def delete_by_payload(self, filter_dict: Dict) -> None:
        """Delete vectors matching a filter."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_dict,
        )
    
    def get_collection_info(self) -> Dict:
        """Get collection statistics."""
        collection_info = self.client.get_collection(self.collection_name)
        return {
            'points_count': collection_info.points_count,
            'vectors_count': collection_info.vectors_count,
            'indexed_vectors_count': collection_info.indexed_vectors_count,
        }
