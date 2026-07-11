"""API views for RAG system."""
import json
import time
from typing import Generator
import google.generativeai as genai
from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rag_api.core.models import Repository, Document, Chunk, QueryLog, QueryResult
from rag_api.api.serializers import (
    RepositorySerializer, DocumentSerializer, ChunkSerializer, QueryResultSerializer
)
from rag_api.retrieval.hybrid_retriever import HybridRetriever
from rag_api.ingestion.tasks import index_repository, rebuild_bm25_index


class RepositoryViewSet(viewsets.ModelViewSet):
    """API endpoints for repository management."""
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    
    @action(detail=False, methods=['post'])
    def index(self, request):
        """Index a GitHub repository."""
        owner = request.data.get('owner')
        name = request.data.get('name')
        branch = request.data.get('branch', 'main')
        
        if not owner or not name:
            return Response(
                {'error': 'owner and name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start async indexing task
        task = index_repository.delay(owner, name, branch)
        
        return Response({
            'status': 'indexing_started',
            'task_id': task.id,
            'owner': owner,
            'name': name,
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['post'])
    def rebuild_index(self, request):
        """Rebuild BM25 index."""
        task = rebuild_bm25_index.delay()
        
        return Response({
            'status': 'rebuilding',
            'task_id': task.id,
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get indexing statistics."""
        repos = Repository.objects.count()
        documents = Document.objects.count()
        chunks = Chunk.objects.count()
        
        return Response({
            'repositories': repos,
            'documents': documents,
            'chunks': chunks,
        })


class DocumentViewSet(viewsets.ModelViewSet):
    """API endpoints for documents."""
    queryset = Document.objects.select_related('repository')
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        """Filter documents by repository if specified."""
        queryset = super().get_queryset()
        repo_id = self.request.query_params.get('repository_id')
        if repo_id:
            queryset = queryset.filter(repository_id=repo_id)
        return queryset


class ChunkViewSet(viewsets.ModelViewSet):
    """API endpoints for chunks."""
    queryset = Chunk.objects.select_related('document', 'document__repository')
    serializer_class = ChunkSerializer
    
    def get_queryset(self):
        """Filter chunks by document if specified."""
        queryset = super().get_queryset()
        doc_id = self.request.query_params.get('document_id')
        if doc_id:
            queryset = queryset.filter(document_id=doc_id)
        return queryset


@require_http_methods(["GET", "POST"])
def query_stream(request):
    """
    Stream query results with server-sent events (SSE).
    
    Query parameters:
        q: search query (required)
        top_k: number of results (default: 5)
        stream: enable streaming (default: true)
    """
    query = request.GET.get('q') or request.POST.get('q')
    top_k = int(request.GET.get('top_k', 5))
    stream_mode = request.GET.get('stream', 'true').lower() == 'true'
    
    if not query:
        return JsonResponse({'error': 'query (q) parameter is required'}, status=400)
    
    def generate_stream() -> Generator[str, None, None]:
        """Generate streaming response with SSE format."""
        try:
            # Start timing
            start_time = time.time()
            
            # Perform hybrid retrieval
            retriever = HybridRetriever()
            results = retriever.retrieve(query, top_k=top_k)
            
            # Log query
            retrieval_time = time.time() - start_time
            query_log = QueryLog.objects.create(
                query_text=query,
                top_k=top_k,
                execution_time_ms=int(retrieval_time * 1000),
                result_count=len(results),
            )
            
            # Stream retrieved context
            context_parts = []
            for rank, (chunk, metadata) in enumerate(results, 1):
                result = QueryResult.objects.create(
                    query_log=query_log,
                    chunk=chunk,
                    rank=rank,
                    bm25_score=metadata.get('bm25_score', 0),
                    vector_score=metadata.get('vector_score', 0),
                    hybrid_score=metadata.get('hybrid_score', 0),
                    rerank_score=metadata.get('rerank_score', 0),
                )
                
                context_parts.append(
                    f"[SOURCE: {chunk.document.file_path} "
                    f"(lines {chunk.start_line}-{chunk.end_line})]\n"
                    f"{chunk.content}\n"
                )
                
                # Emit retrieval event
                event_data = {
                    'type': 'retrieval',
                    'rank': rank,
                    'chunk_id': str(chunk.id),
                    'file_path': chunk.document.file_path,
                    'content': chunk.content,
                    'scores': {
                        'bm25': metadata.get('bm25_score', 0),
                        'vector': metadata.get('vector_score', 0),
                        'hybrid': metadata.get('hybrid_score', 0),
                        'rerank': metadata.get('rerank_score', 0),
                    },
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            # Generate LLM response using retrieved context
            context = "\n".join(context_parts)
            system_prompt = (
                "You are a helpful AI assistant. Use the provided sources to answer "
                "the user's question. Always cite the sources by referencing the file path "
                "and line numbers provided in the SOURCE tags. If you cannot answer based "
                "on the provided sources, say so explicitly."
            )
            
            user_message = f"""Based on the following sources, please answer this question:

{context}

Question: {query}"""
            
            # Stream LLM response
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                settings.LLM_MODEL,
                system_instruction=system_prompt,
            )

            stream = model.generate_content(
                user_message,
                stream=True,
                generation_config={"max_output_tokens": 1024},
            )
            full_response = ""
            for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
                    event_data = {
                        'type': 'response',
                        'content': chunk.text,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
            
            # Send completion event
            completion_event = {
                'type': 'complete',
                'query': query,
                'retrieval_time_ms': int(retrieval_time * 1000),
                'sources_count': len(results),
            }
            yield f"data: {json.dumps(completion_event)}\n\n"
        
        except Exception as e:
            error_event = {
                'type': 'error',
                'error': str(e),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingHttpResponse(
        generate_stream(),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint."""
    try:
        # Check database
        Document.objects.count()
        
        # Check basic stats
        stats = {
            'status': 'healthy',
            'documents': Document.objects.count(),
            'chunks': Chunk.objects.count(),
            'queries_logged': QueryLog.objects.count(),
        }
        
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
        }, status=500)
