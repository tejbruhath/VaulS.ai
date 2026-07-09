"""DRF Serializers for API."""
from rest_framework import serializers
from rag_api.core.models import Repository, Document, Chunk


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model."""
    
    class Meta:
        model = Repository
        fields = ['id', 'owner', 'name', 'url', 'branch', 'last_indexed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_indexed']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""
    repository_display = serializers.StringRelatedField(
        source='repository',
        read_only=True
    )
    
    class Meta:
        model = Document
        fields = ['id', 'repository', 'repository_display', 'file_path', 'file_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChunkSerializer(serializers.ModelSerializer):
    """Serializer for Chunk model."""
    document_file_path = serializers.CharField(
        source='document.file_path',
        read_only=True
    )
    document_id = serializers.UUIDField(
        source='document.id',
        read_only=True
    )
    
    class Meta:
        model = Chunk
        fields = [
            'id', 'document_id', 'document_file_path', 'content',
            'chunk_index', 'start_line', 'end_line', 'token_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class QueryResultSerializer(serializers.Serializer):
    """Serializer for query results."""
    chunk_id = serializers.CharField()
    content = serializers.CharField()
    file_path = serializers.CharField()
    start_line = serializers.IntegerField(required=False)
    end_line = serializers.IntegerField(required=False)
    bm25_score = serializers.FloatField()
    vector_score = serializers.FloatField()
    hybrid_score = serializers.FloatField()
    rerank_score = serializers.FloatField()
