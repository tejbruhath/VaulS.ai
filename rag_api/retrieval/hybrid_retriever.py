"""Hybrid retrieval combining BM25 and vector search."""
from typing import List, Dict, Tuple
import numpy as np
from django.conf import settings
from .bm25_index import BM25Manager
from .vector_store import VectorStore
from .embeddings import EmbeddingService
from rag_api.core.models import Chunk, QueryLog, QueryResult


class HybridRetriever:
    """Combines BM25 and dense vector retrieval with re-ranking."""
    
    def __init__(self):
        """Initialize retriever with all components."""
        from .index_manager import IndexManager
        
        self.index_manager = IndexManager()
        self.bm25 = self.index_manager.get_bm25_index()
        self.vector_store = self.index_manager.get_vector_store()
        self.embedding_service = EmbeddingService()
        self.weight_bm25 = settings.HYBRID_WEIGHT_BM25
        self.weight_vector = settings.HYBRID_WEIGHT_VECTOR
        self.rerank_top_k = settings.RERANK_TOP_K
        self.final_top_k = settings.FINAL_TOP_K
    
    def retrieve(self, query: str, top_k: int = None) -> List[Tuple[Chunk, Dict]]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of final results to return
        
        Returns:
            List of (Chunk, metadata) tuples
        """
        if top_k is None:
            top_k = self.final_top_k
        
        # Get all chunks
        all_chunks = Chunk.objects.select_related('document').all()
        if not all_chunks.exists():
            return []
        
        # Build BM25 index if needed
        if self.bm25.bm25 is None:
            self._build_bm25_index(all_chunks)
        
        # 1. BM25 sparse retrieval
        bm25_results = self._bm25_search(query, top_k=self.rerank_top_k)
        
        # 2. Dense vector search
        vector_results = self._vector_search(query, top_k=self.rerank_top_k)
        
        # 3. Combine and normalize scores
        combined_results = self._combine_results(
            bm25_results, vector_results, all_chunks
        )
        
        # 4. Re-rank using semantic similarity
        reranked = self._rerank(query, combined_results)
        
        # 5. Return top-k results
        return reranked[:top_k]
    
    def _build_bm25_index(self, chunks):
        """Build BM25 index from all chunks."""
        documents = [
            (str(chunk.id), chunk.content)
            for chunk in chunks
        ]
        self.bm25.build_index(documents)
    
    def _bm25_search(self, query: str, top_k: int) -> Dict[str, float]:
        """BM25 search returning chunk IDs and scores."""
        results = self.bm25.search(query, top_k=top_k)
        
        # Map back to chunk IDs
        all_chunks = list(Chunk.objects.all().values_list('id', flat=True))
        
        chunk_scores = {}
        for chunk_idx, score in results:
            if chunk_idx < len(all_chunks):
                chunk_id = all_chunks[chunk_idx]
                chunk_scores[str(chunk_id)] = score
        
        return chunk_scores
    
    def _vector_search(self, query: str, top_k: int) -> Dict[str, float]:
        """Vector search returning chunk IDs and scores."""
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Search in Qdrant
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        chunk_scores = {}
        for point_id, score, metadata in results:
            chunk_id = metadata.get('chunk_id')
            if chunk_id:
                chunk_scores[chunk_id] = score
        
        return chunk_scores
    
    def _combine_results(self, bm25_results: Dict[str, float],
                        vector_results: Dict[str, float],
                        all_chunks) -> List[Tuple[Chunk, float]]:
        """Combine and normalize BM25 and vector scores."""
        all_chunk_ids = set(bm25_results.keys()) | set(vector_results.keys())
        combined = []
        
        # Normalize scores
        bm25_max = max(bm25_results.values()) if bm25_results else 1.0
        vector_max = max(vector_results.values()) if vector_results else 1.0
        
        for chunk_id in all_chunk_ids:
            bm25_score = bm25_results.get(chunk_id, 0) / max(bm25_max, 1.0)
            vector_score = vector_results.get(chunk_id, 0) / max(vector_max, 1.0)
            
            hybrid_score = (
                self.weight_bm25 * bm25_score +
                self.weight_vector * vector_score
            )
            
            chunk = Chunk.objects.get(id=chunk_id)
            combined.append((chunk, {
                'bm25_score': bm25_score,
                'vector_score': vector_score,
                'hybrid_score': hybrid_score,
            }))
        
        # Sort by hybrid score
        combined.sort(key=lambda x: x[1]['hybrid_score'], reverse=True)
        
        return combined
    
    def _rerank(self, query: str, 
               candidates: List[Tuple[Chunk, Dict]]) -> List[Tuple[Chunk, Dict]]:
        """Re-rank candidates using semantic similarity."""
        if not candidates:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Generate embeddings for all candidates
        candidate_texts = [chunk.content for chunk, _ in candidates]
        candidate_embeddings = self.embedding_service.embed_batch(candidate_texts)
        
        # Compute similarity scores
        reranked = []
        for (chunk, metadata), embedding in zip(candidates, candidate_embeddings):
            # Cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-10
            )
            metadata['rerank_score'] = similarity
            reranked.append((chunk, metadata))
        
        # Sort by re-rank score
        reranked.sort(key=lambda x: x[1]['rerank_score'], reverse=True)
        
        return reranked
