"""Advanced Qdrant collection management."""
from typing import List, Dict, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, PayloadSchemaType
)
from django.conf import settings

logger = logging.getLogger(__name__)


class QdrantCollectionManager:
    """Manage Qdrant collections with advanced features."""
    
    def __init__(self, collection_name: str = "documents", vector_size: int = 1536):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    
    def create_collection_with_schema(self) -> None:
        """Create collection with optimized schema."""
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception:
            logger.info(f"Creating collection '{self.collection_name}'...")
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
                # Set payload schema for type hints
                payload_schema_config={
                    "chunk_id": PayloadSchemaType.KEYWORD,
                    "document_id": PayloadSchemaType.KEYWORD,
                    "file_path": PayloadSchemaType.TEXT,
                    "repository": PayloadSchemaType.KEYWORD,
                },
            )
            logger.info(f"Collection created successfully")
    
    def create_snapshot(self) -> Optional[str]:
        """Create backup snapshot of collection."""
        try:
            snapshot_description = self.client.snapshot(
                self.collection_name
            )
            logger.info(f"Snapshot created: {snapshot_description.file_name}")
            return snapshot_description.file_name
        except Exception as e:
            logger.error(f"Failed to create snapshot: {str(e)}")
            return None
    
    def list_snapshots(self) -> List[str]:
        """List available snapshots."""
        try:
            snapshots = self.client.list_snapshots(self.collection_name)
            return [s.file_name for s in snapshots]
        except Exception as e:
            logger.error(f"Failed to list snapshots: {str(e)}")
            return []
    
    def search_with_filter(self, embedding: List[float], 
                          filter_dict: Dict = None,
                          top_k: int = 10) -> List[Dict]:
        """Search with optional filtering."""
        # Build Qdrant filter from dict
        query_filter = None
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            query_filter = Filter(must=conditions)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        
        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]
    
    def delete_by_filter(self, filter_dict: Dict) -> int:
        """Delete points matching filter."""
        conditions = []
        for key, value in filter_dict.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )
        
        query_filter = Filter(must=conditions)
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=query_filter,
        )
        
        logger.info(f"Deleted {result.deleted} points")
        return result.deleted
    
    def optimize_collection(self) -> None:
        """Optimize collection for better performance."""
        try:
            self.client.optimize_collections(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' optimized")
        except Exception as e:
            logger.error(f"Failed to optimize collection: {str(e)}")
    
    def get_collection_stats(self) -> Dict:
        """Get detailed collection statistics."""
        try:
            collection = self.client.get_collection(self.collection_name)
            return {
                "points_count": collection.points_count,
                "vectors_count": collection.vectors_count,
                "indexed_vectors_count": collection.indexed_vectors_count,
                "segment_count": len(collection.config.params.segment_type),
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
    
    def recreate_collection(self) -> None:
        """Recreate collection (dangerous - deletes data)."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.warning(f"Collection '{self.collection_name}' deleted")
        except Exception as e:
            logger.warning(f"Collection did not exist: {str(e)}")
        
        self.create_collection_with_schema()
    
    def health_check(self) -> bool:
        """Check Qdrant server health."""
        try:
            health = self.client.get_telemetry()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False


class VectorSearchCache:
    """Cache for vector search results to improve performance."""
    
    def __init__(self, ttl: int = 3600):
        from django.core.cache import cache
        self.cache = cache
        self.ttl = ttl
    
    def get_cache_key(self, embedding_hash: str, top_k: int) -> str:
        """Generate cache key."""
        return f"vec_search:{embedding_hash}:topk{top_k}"
    
    def cache_result(self, embedding_hash: str, top_k: int, results: List[Dict]) -> None:
        """Cache search results."""
        key = self.get_cache_key(embedding_hash, top_k)
        self.cache.set(key, results, timeout=self.ttl)
    
    def get_cached_result(self, embedding_hash: str, top_k: int) -> Optional[List[Dict]]:
        """Retrieve cached results."""
        key = self.get_cache_key(embedding_hash, top_k)
        return self.cache.get(key)
    
    def clear_cache(self) -> None:
        """Clear all search caches."""
        # In practice, use cache.delete_pattern if available
        pass
