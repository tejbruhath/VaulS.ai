"""Database models for RAG system."""
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Repository(models.Model):
    """GitHub repository metadata."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    url = models.URLField()
    branch = models.CharField(max_length=255, default='main')
    last_indexed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'name')
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['last_indexed']),
        ]

    def __str__(self):
        return f"{self.owner}/{self.name}"


class Document(models.Model):
    """Source document/file."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='documents')
    file_path = models.TextField()
    content = models.TextField()
    file_type = models.CharField(max_length=50)  # 'markdown', 'python', 'json', etc.
    sha256_hash = models.CharField(max_length=64, unique=True)  # For deduplication
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['repository', 'file_path']),
            models.Index(fields=['sha256_hash']),
            models.Index(fields=['file_type']),
        ]

    def __str__(self):
        return f"{self.file_path} ({self.repository})"


class Chunk(models.Model):
    """Semantic chunk of a document."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()  # Order within document
    start_line = models.IntegerField(null=True, blank=True)
    end_line = models.IntegerField(null=True, blank=True)
    token_count = models.IntegerField(default=0)
    
    # BM25 index (stored as JSONB for flexibility)
    bm25_tokens = ArrayField(models.CharField(max_length=255), default=list)
    bm25_term_frequencies = models.JSONField(default=dict)
    
    # Vector metadata
    embedding_id = models.CharField(max_length=36, null=True, blank=True)  # Qdrant point_id
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['embedding_id']),
        ]
        unique_together = ('document', 'chunk_index')

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.file_path}"


class BM25Index(models.Model):
    """Global BM25 index metadata."""
    id = models.AutoField(primary_key=True)
    idf_map = models.JSONField(default=dict)  # term -> idf score
    num_docs = models.IntegerField(default=0)
    avg_doc_len = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "BM25 Indexes"

    def __str__(self):
        return f"BM25 Index (docs={self.num_docs})"


class QueryLog(models.Model):
    """Log of queries for analytics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField()
    top_k = models.IntegerField(default=5)
    hybrid_weight_bm25 = models.FloatField(default=0.3)
    hybrid_weight_vector = models.FloatField(default=0.7)
    execution_time_ms = models.IntegerField()
    result_count = models.IntegerField()
    chunks_retrieved = models.ManyToManyField(Chunk, through='QueryResult')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Query: {self.query_text[:50]}..."


class QueryResult(models.Model):
    """Ranking of chunks returned for a query."""
    id = models.AutoField(primary_key=True)
    query_log = models.ForeignKey(QueryLog, on_delete=models.CASCADE)
    chunk = models.ForeignKey(Chunk, on_delete=models.CASCADE)
    rank = models.IntegerField()
    bm25_score = models.FloatField(default=0.0)
    vector_score = models.FloatField(default=0.0)
    hybrid_score = models.FloatField(default=0.0)
    rerank_score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('query_log', 'chunk', 'rank')
        indexes = [
            models.Index(fields=['query_log', 'rank']),
        ]

    def __str__(self):
        return f"Result Rank {self.rank}: {self.hybrid_score:.3f}"
