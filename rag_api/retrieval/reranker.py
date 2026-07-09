"""Advanced re-ranking strategies."""
import numpy as np
import logging
from typing import List, Tuple, Dict
from sentence_transformers import CrossEncoderModel
from django.conf import settings

logger = logging.getLogger(__name__)


class SemanticReranker:
    """Re-rank candidates using semantic similarity and neural models."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize re-ranker with pre-trained model."""
        try:
            self.model = CrossEncoderModel(model_name)
            logger.info(f"Loaded cross-encoder model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {str(e)}, using fallback")
            self.model = None
    
    def rerank_with_cross_encoder(self, query: str, 
                                  candidates: List[Tuple]) -> List[Tuple]:
        """
        Re-rank candidates using cross-encoder model.
        
        Args:
            query: The search query
            candidates: List of (chunk, metadata) tuples
        
        Returns:
            Re-ranked list of (chunk, metadata) tuples
        """
        if not candidates or self.model is None:
            return candidates
        
        try:
            # Prepare pairs for cross-encoder
            query_chunk_pairs = [
                [query, chunk.content]
                for chunk, _ in candidates
            ]
            
            # Get scores from cross-encoder
            scores = self.model.predict(query_chunk_pairs)
            
            # Update metadata with cross-encoder scores
            for (chunk, metadata), score in zip(candidates, scores):
                metadata['cross_encoder_score'] = float(score)
            
            # Re-rank by cross-encoder score
            candidates.sort(key=lambda x: x[1]['cross_encoder_score'], reverse=True)
            
            return candidates
        except Exception as e:
            logger.error(f"Cross-encoder re-ranking failed: {str(e)}")
            return candidates
    
    def rerank_with_semantic_similarity(self, query_embedding: List[float],
                                       candidates: List[Tuple]) -> List[Tuple]:
        """
        Re-rank using semantic similarity scores.
        
        Args:
            query_embedding: The query embedding vector
            candidates: List of (chunk, metadata) tuples with candidate embeddings
        
        Returns:
            Re-ranked list sorted by semantic similarity
        """
        query_vec = np.array(query_embedding)
        
        similarities = []
        for chunk, metadata in candidates:
            # Compute cosine similarity with candidate
            # In practice, you'd have the candidate embedding stored
            similarity = metadata.get('rerank_score', 0)
            similarities.append(similarity)
        
        # Re-rank by similarity
        indexed = list(enumerate(zip(candidates, similarities)))
        indexed.sort(key=lambda x: x[1][1], reverse=True)
        
        return [cand for _, (cand, _) in indexed]
    
    def diversity_rerank(self, candidates: List[Tuple], 
                        diversity_factor: float = 0.3) -> List[Tuple]:
        """
        Apply diversity re-ranking to reduce redundancy.
        
        Args:
            candidates: List of (chunk, metadata) tuples
            diversity_factor: Weight for diversity (0-1)
        
        Returns:
            Re-ranked list with diversity consideration
        """
        if not candidates:
            return candidates
        
        reranked = []
        remaining = list(candidates)
        
        # Add first candidate (highest scored)
        if remaining:
            best = max(remaining, key=lambda x: x[1].get('rerank_score', 0))
            reranked.append(best)
            remaining.remove(best)
        
        # Add remaining candidates with diversity penalty
        while remaining:
            best_candidate = None
            best_score = -float('inf')
            
            for candidate in remaining:
                chunk, metadata = candidate
                base_score = metadata.get('rerank_score', 0)
                
                # Penalize if similar to already selected
                diversity_penalty = 0
                for selected_chunk, _ in reranked:
                    # Simple similarity check - can be improved with embeddings
                    if self._content_similarity(chunk.content, selected_chunk.content) > 0.7:
                        diversity_penalty += diversity_factor
                
                adjusted_score = base_score * (1 - diversity_penalty)
                
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_candidate = candidate
            
            if best_candidate:
                reranked.append(best_candidate)
                remaining.remove(best_candidate)
        
        return reranked
    
    def _content_similarity(self, text1: str, text2: str) -> float:
        """Simple string similarity for diversity checking."""
        # Convert to sets of words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0


class QueryExpander:
    """Expand queries for better retrieval."""
    
    @staticmethod
    def expand_with_synonyms(query: str) -> List[str]:
        """
        Expand query with potential synonyms.
        
        This is a simple implementation - can be improved with
        thesaurus APIs or embedding-based approaches.
        """
        # Simple synonym mapping for common terms
        synonym_map = {
            'setup': ['install', 'configure', 'initialize'],
            'use': ['utilize', 'apply', 'employ'],
            'error': ['issue', 'problem', 'bug', 'failure'],
            'deploy': ['launch', 'release', 'publish'],
            'build': ['create', 'construct', 'compile'],
            'test': ['verify', 'validate', 'check'],
        }
        
        expanded = [query]
        for word, synonyms in synonym_map.items():
            if word in query.lower():
                for synonym in synonyms:
                    expanded.append(query.replace(word, synonym))
        
        return expanded
    
    @staticmethod
    def expand_with_ngrams(query: str, n: int = 2) -> List[str]:
        """Generate n-gram variants of query."""
        tokens = query.split()
        
        if len(tokens) <= n:
            return [query]
        
        # Generate subsequences
        variations = [query]
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            variations.append(ngram)
        
        return variations
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize query for better matching."""
        # Lowercase
        query = query.lower()
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove punctuation
        import string
        query = query.translate(str.maketrans('', '', string.punctuation))
        
        return query
