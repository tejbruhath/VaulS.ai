#!/usr/bin/env python
"""Optimize RAG system for production."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.core.management import call_command
from django.db import connection
from rag_api.core.models import Chunk, Document, Repository
from rag_api.retrieval.index_manager import OptimizedIndexBuilder
from rag_api.retrieval.qdrant_manager import QdrantCollectionManager
import logging

logger = logging.getLogger(__name__)


def optimize_database():
    """Optimize PostgreSQL database."""
    print("\n[1] Optimizing PostgreSQL database...")
    
    with connection.cursor() as cursor:
        # Vacuum and analyze
        cursor.execute("VACUUM ANALYZE")
        
        # Create indices
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_chunk_document ON core_chunk(document_id, chunk_index)",
            "CREATE INDEX IF NOT EXISTS idx_document_repository ON core_document(repository_id, file_path)",
            "CREATE INDEX IF NOT EXISTS idx_querylog_created ON core_querylog(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_queryresult_rank ON core_queryresult(query_log_id, rank)",
        ]
        
        for idx_sql in indices:
            try:
                cursor.execute(idx_sql)
                print(f"  ✓ {idx_sql.split('ON')[1].strip()}")
            except Exception as e:
                print(f"  ✗ {idx_sql.split('ON')[1].strip()}: {str(e)}")
    
    print("  Database optimization complete!")


def optimize_qdrant():
    """Optimize Qdrant vector store."""
    print("\n[2] Optimizing Qdrant collection...")
    
    try:
        manager = QdrantCollectionManager()
        
        # Check health
        if manager.health_check():
            print("  ✓ Qdrant server is healthy")
        else:
            print("  ✗ Qdrant server health check failed")
            return
        
        # Get collection stats
        stats = manager.get_collection_stats()
        print(f"  • Points: {stats.get('points_count', 0)}")
        print(f"  • Vectors: {stats.get('vectors_count', 0)}")
        print(f"  • Indexed: {stats.get('indexed_vectors_count', 0)}")
        
        # Optimize collection
        manager.optimize_collection()
        print("  ✓ Collection optimized")
        
        # Create snapshot
        snapshot = manager.create_snapshot()
        if snapshot:
            print(f"  ✓ Snapshot created: {snapshot}")
    
    except Exception as e:
        print(f"  ✗ Qdrant optimization failed: {str(e)}")


def rebuild_indices():
    """Rebuild search indices."""
    print("\n[3] Rebuilding search indices...")
    
    try:
        chunks = Chunk.objects.count()
        print(f"  Found {chunks} chunks to index")
        
        if chunks == 0:
            print("  ⚠ No chunks to index")
            return
        
        builder = OptimizedIndexBuilder(batch_size=100)
        builder.rebuild_all_indices()
        print("  ✓ Indices rebuilt successfully")
    
    except Exception as e:
        print(f"  ✗ Index rebuild failed: {str(e)}")


def cleanup_old_logs():
    """Clean up old query logs."""
    print("\n[4] Cleaning up old query logs...")
    
    from django.utils import timezone
    from datetime import timedelta
    from rag_api.core.models import QueryLog
    
    try:
        cutoff = timezone.now() - timedelta(days=30)
        deleted_count, _ = QueryLog.objects.filter(created_at__lt=cutoff).delete()
        print(f"  ✓ Deleted {deleted_count} old query logs")
    
    except Exception as e:
        print(f"  ✗ Cleanup failed: {str(e)}")


def check_index_stats():
    """Print index statistics."""
    print("\n[5] Index Statistics...")
    
    try:
        repos = Repository.objects.count()
        docs = Document.objects.count()
        chunks = Chunk.objects.count()
        
        print(f"  • Repositories: {repos}")
        print(f"  • Documents: {docs}")
        print(f"  • Chunks: {chunks}")
        
        if chunks > 0:
            avg_chunk_size = sum(c.token_count for c in Chunk.objects.all()) / chunks
            print(f"  • Avg chunk size: {avg_chunk_size:.0f} tokens")
    
    except Exception as e:
        print(f"  ✗ Failed to get stats: {str(e)}")


def main():
    """Run all optimizations."""
    print("=" * 60)
    print("RAG System Optimization")
    print("=" * 60)
    
    optimize_database()
    optimize_qdrant()
    rebuild_indices()
    cleanup_old_logs()
    check_index_stats()
    
    print("\n" + "=" * 60)
    print("Optimization complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
