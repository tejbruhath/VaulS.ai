"""Index management and persistence."""
import pickle
import json
import logging
from pathlib import Path
from typing import Optional
from django.core.cache import cache
from django.conf import settings
from django.core.files.storage import default_storage
from .bm25_index import BM25Manager
from .vector_store import VectorStore
from rag_api.core.models import BM25Index as BM25IndexModel

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages BM25 and vector index persistence and caching."""
    
    BM25_CACHE_KEY = 'rag:bm25_index'
    BM25_CACHE_TIMEOUT = 86400 * 7  # 7 days
    BM25_FILE_PATH = 'indices/bm25_index.pkl'
    
    def __init__(self):
        self.bm25 = None
        self.vector_store = None
        self._load_indices()
    
    def _load_indices(self):
        """Load indices from cache or disk."""
        # Try loading from cache first
        self.bm25 = cache.get(self.BM25_CACHE_KEY)
        
        if self.bm25 is None:
            # Try loading from disk
            self.bm25 = self._load_bm25_from_disk()
        
        # Initialize vector store (always fresh connection)
        self.vector_store = VectorStore()
    
    def _load_bm25_from_disk(self) -> Optional[BM25Manager]:
        """Load BM25 index from disk."""
        try:
            if default_storage.exists(self.BM25_FILE_PATH):
                with default_storage.open(self.BM25_FILE_PATH, 'rb') as f:
                    return pickle.load(f)
            
            # Try loading from database
            bm25_model = BM25IndexModel.objects.first()
            if bm25_model:
                bm25 = BM25Manager()
                bm25.idf_map = bm25_model.idf_map
                bm25.corpus_size = bm25_model.num_docs
                bm25.avg_doc_len = bm25_model.avg_doc_len
                return bm25
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {str(e)}")
        
        return None
    
    def save_bm25_index(self, bm25: BM25Manager):
        """Save BM25 index to cache and disk."""
        try:
            # Save to cache
            cache.set(self.BM25_CACHE_KEY, bm25, timeout=self.BM25_CACHE_TIMEOUT)
            
            # Save to disk
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp_file:
                pickle.dump(bm25, tmp_file)
                tmp_file.flush()
                
                with open(tmp_file.name, 'rb') as f:
                    default_storage.save(self.BM25_FILE_PATH, f)
            
            logger.info(f"BM25 index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {str(e)}")
    
    def get_bm25_index(self) -> Optional[BM25Manager]:
        """Get BM25 index, loading from cache if needed."""
        if self.bm25 is None:
            self._load_indices()
        return self.bm25
    
    def get_vector_store(self) -> VectorStore:
        """Get vector store."""
        if self.vector_store is None:
            self.vector_store = VectorStore()
        return self.vector_store
    
    def get_index_stats(self) -> dict:
        """Get combined index statistics."""
        stats = {
            'bm25': {},
            'vector': {},
        }
        
        # Get BM25 stats
        if self.bm25:
            bm25_stats = self.bm25.get_index_stats()
            stats['bm25'] = {
                'corpus_size': bm25_stats['corpus_size'],
                'avg_doc_len': bm25_stats['avg_doc_len'],
                'vocabulary_size': bm25_stats['vocabulary_size'],
            }
        
        # Get vector store stats
        try:
            vector_stats = self.vector_store.get_collection_info()
            stats['vector'] = vector_stats
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {str(e)}")
        
        return stats


class OptimizedIndexBuilder:
    """Optimized builder for creating indices."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.index_manager = IndexManager()
    
    def build_bm25_from_chunks(self, chunks) -> BM25Manager:
        """Build BM25 index from chunks efficiently."""
        bm25 = BM25Manager()
        documents = []
        
        for chunk in chunks:
            documents.append((str(chunk.id), chunk.content))
            
            # Build in batches
            if len(documents) >= self.batch_size:
                bm25.build_index(documents)
                documents = []
        
        # Build final batch
        if documents:
            bm25.build_index(documents)
        
        # Save index
        self.index_manager.save_bm25_index(bm25)
        
        return bm25
    
    def build_vector_embeddings_batch(self, chunks, embedding_service) -> list:
        """Build vector embeddings efficiently using batch API."""
        from rag_api.core.models import Chunk
        vector_store = self.index_manager.get_vector_store()
        
        # Process chunks in batches
        all_chunk_texts = [chunk.content for chunk in chunks]
        all_embeddings = embedding_service.embed_batch(all_chunk_texts)
        
        # Get existing point IDs for upsert
        point_ids = []
        for chunk, embedding in zip(chunks, all_embeddings):
            # Skip if already embedded
            if chunk.embedding_id:
                continue
            
            metadata = {
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document.id),
                'file_path': chunk.document.file_path,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
            }
            
            point_id = vector_store.add_vector(embedding, metadata)
            point_ids.append(point_id)
        
        return point_ids
    
    def rebuild_all_indices(self):
        """Rebuild all indices from database chunks."""
        from rag_api.core.models import Chunk
        from rag_api.retrieval.embeddings import EmbeddingService
        
        logger.info("Starting full index rebuild...")
        
        chunks = Chunk.objects.select_related('document').all()
        
        # Build BM25
        logger.info(f"Building BM25 index for {chunks.count()} chunks...")
        bm25 = self.build_bm25_from_chunks(chunks)
        logger.info(f"BM25 index built: {bm25.get_index_stats()}")
        
        # Build vectors
        logger.info("Building vector embeddings...")
        embedding_service = EmbeddingService()
        self.build_vector_embeddings_batch(chunks, embedding_service)
        logger.info("Vector embeddings built")
        
        logger.info("Index rebuild complete")
