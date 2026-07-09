"""BM25 sparse retrieval index."""
import math
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from django.db import models


class BM25Manager:
    """Manages BM25 indexing and retrieval."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 with parameters.
        
        Args:
            k1: Controls term frequency saturation (default 1.5)
            b: Controls length normalization (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.bm25 = None
        self.tokenized_docs = []
        self.idf_map = {}
        self.corpus_size = 0
        self.avg_doc_len = 0.0
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple tokenization."""
        # Lowercase and split on whitespace and punctuation
        import re
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens
    
    def build_index(self, documents: List[Tuple[str, str]]) -> None:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of (doc_id, text) tuples
        """
        self.tokenized_docs = []
        self.corpus_size = len(documents)
        
        total_tokens = 0
        for doc_id, text in documents:
            tokens = self.tokenize(text)
            self.tokenized_docs.append(tokens)
            total_tokens += len(tokens)
        
        if self.corpus_size > 0:
            self.avg_doc_len = total_tokens / self.corpus_size
        
        self.bm25 = BM25Okapi(self.tokenized_docs, k1=self.k1, b=self.b)
        
        # Build IDF map
        self._build_idf_map()
    
    def _build_idf_map(self) -> None:
        """Build IDF map for analytics."""
        self.idf_map = {}
        
        for token in set(token for doc_tokens in self.tokenized_docs 
                         for token in doc_tokens):
            # Calculate IDF
            docs_with_token = sum(1 for doc_tokens in self.tokenized_docs 
                                  if token in doc_tokens)
            idf = math.log((self.corpus_size - docs_with_token + 0.5) / 
                          (docs_with_token + 0.5) + 1.0)
            self.idf_map[token] = idf
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for top-k documents.
        
        Returns:
            List of (doc_index, score) tuples
        """
        if self.bm25 is None:
            return []
        
        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        
        return [(idx, score) for idx, score in top_indices if score > 0]
    
    def get_index_stats(self) -> Dict:
        """Get index statistics."""
        return {
            'corpus_size': self.corpus_size,
            'avg_doc_len': self.avg_doc_len,
            'vocabulary_size': len(self.idf_map),
            'k1': self.k1,
            'b': self.b,
        }
