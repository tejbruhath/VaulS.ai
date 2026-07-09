"""Django admin configuration."""
from django.contrib import admin
from .models import Repository, Document, Chunk, BM25Index, QueryLog, QueryResult


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'branch', 'last_indexed')
    search_fields = ('owner', 'name', 'url')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file_path', 'repository', 'file_type', 'updated_at')
    search_fields = ('file_path', 'repository__name')
    readonly_fields = ('id', 'sha256_hash', 'created_at', 'updated_at')
    list_filter = ('file_type', 'repository')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'chunk_index', 'token_count', 'embedding_id')
    search_fields = ('document__file_path', 'content')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_filter = ('document__repository',)


@admin.register(BM25Index)
class BM25IndexAdmin(admin.ModelAdmin):
    list_display = ('id', 'num_docs', 'avg_doc_len', 'last_updated')
    readonly_fields = ('last_updated',)


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'result_count', 'execution_time_ms', 'created_at')
    search_fields = ('query_text',)
    readonly_fields = ('id', 'created_at')
    list_filter = ('created_at',)


@admin.register(QueryResult)
class QueryResultAdmin(admin.ModelAdmin):
    list_display = ('query_log', 'rank', 'hybrid_score', 'rerank_score')
    readonly_fields = ('id',)
    list_filter = ('rank',)
