"""Celery tasks for indexing."""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
import hashlib
import logging
from .github_loader import GitHubLoader
from .chunking import SemanticChunker
from .utils import ChunkingValidator, RepositoryIngestionValidator
from rag_api.core.models import Repository, Document, Chunk, BM25Index
from rag_api.retrieval.embeddings import EmbeddingService
from rag_api.retrieval.vector_store import VectorStore
from rag_api.retrieval.bm25_index import BM25Manager

logger = logging.getLogger(__name__)


@shared_task
def index_repository(owner: str, name: str, branch: str = 'main'):
    """
    Index a GitHub repository.
    
    Args:
        owner: GitHub owner/organization
        name: Repository name
        branch: Branch to index (default: main)
    """
    try:
        # Get or create repository record
        repo, created = Repository.objects.get_or_create(
            owner=owner,
            name=name,
            defaults={'branch': branch, 'url': f'https://github.com/{owner}/{name}'}
        )
        
        # Load repository from GitHub
        loader = GitHubLoader()
        temp_dir, files = loader.load_repository(owner, name, branch)
        
        # Index files
        for file_path, content, file_type in files:
            # Compute content hash for deduplication
            content_hash = loader.compute_file_hash(content)
            
            # Check if document already exists and has same content
            existing_doc = Document.objects.filter(
                sha256_hash=content_hash
            ).first()
            
            if existing_doc:
                # Update repository reference if needed
                if existing_doc.repository_id != repo.id:
                    existing_doc.repository = repo
                    existing_doc.save()
                continue
            
            # Create document
            doc = Document.objects.create(
                repository=repo,
                file_path=file_path,
                content=content,
                file_type=file_type,
                sha256_hash=content_hash,
            )
            
            # Chunk document
            chunker = SemanticChunker(
                chunk_size=512,
                overlap=100,
            )
            chunks = chunker.chunk(content, file_type)
            
            # Validate chunks
            valid_chunks = []
            for chunk in chunks:
                validation = ChunkingValidator.validate_chunk(chunk.content)
                if validation['valid']:
                    valid_chunks.append(chunk)
                else:
                    logger.warning(f"Chunk validation failed for {file_path}: {validation['issues']}")
            
            if not valid_chunks:
                logger.warning(f"No valid chunks found for {file_path}, skipping")
                continue
            
            # Create chunk records and index
            embedding_service = EmbeddingService()
            vector_store = VectorStore()
            
            for chunk in valid_chunks:
                # Create chunk in database
                chunk_obj = Chunk.objects.create(
                    document=doc,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    token_count=chunk.token_count,
                    bm25_tokens=BM25Manager.tokenize(chunk.content),
                )
                
                # Generate embedding
                embedding = embedding_service.embed_text(chunk.content)
                
                # Store in vector database
                point_id = vector_store.add_vector(
                    embedding=embedding,
                    metadata={
                        'chunk_id': str(chunk_obj.id),
                        'document_id': str(doc.id),
                        'file_path': file_path,
                        'start_line': chunk.start_line,
                        'end_line': chunk.end_line,
                    },
                )
                
                # Update chunk with embedding ID
                chunk_obj.embedding_id = point_id
                chunk_obj.save()
        
        # Update repository last_indexed time
        repo.last_indexed = timezone.now()
        repo.save()
        
        # Clear retriever cache
        cache.delete('bm25_index')
        
        return {
            'status': 'success',
            'owner': owner,
            'name': name,
            'files_indexed': len(files),
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'owner': owner,
            'name': name,
            'error': str(e),
        }


@shared_task
def rebuild_bm25_index():
    """Rebuild BM25 index from all documents in database."""
    try:
        from rag_api.retrieval.index_manager import OptimizedIndexBuilder
        
        builder = OptimizedIndexBuilder(batch_size=100)
        
        # Fetch all chunks
        all_chunks = Chunk.objects.all()
        
        # Build using optimized builder
        bm25 = builder.build_bm25_from_chunks(all_chunks)
        
        # Store index stats in database
        stats = bm25.get_index_stats()
        BM25Index.objects.update_or_create(
            id=1,
            defaults={
                'idf_map': bm25.idf_map,
                'num_docs': stats['corpus_size'],
                'avg_doc_len': stats['avg_doc_len'],
            }
        )
        
        logger.info(f"BM25 index rebuilt: {stats}")
        
        return {
            'status': 'success',
            'documents_indexed': stats['corpus_size'],
            'vocabulary_size': stats['vocabulary_size'],
        }
    
    except Exception as e:
        logger.error(f"BM25 rebuild failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
        }
