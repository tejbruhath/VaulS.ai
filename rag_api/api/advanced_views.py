"""Advanced API endpoints for RAG system."""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework import status
from rag_api.retrieval.hybrid_retriever import HybridRetriever
from rag_api.api.citations import (
    CitationFormatter, SourceAttributionBuilder, InlineCircationExtractor
)
from rag_api.retrieval.reranker import QueryExpander
from rag_api.core.models import QueryLog, Repository


@require_http_methods(["GET"])
def query_with_citations(request):
    """
    Query endpoint returning structured citations.
    
    Query parameters:
        q: search query
        top_k: number of results
        citation_format: markdown|html|json|bibtex (default: json)
    """
    query = request.GET.get('q')
    top_k = int(request.GET.get('top_k', 5))
    citation_format = request.GET.get('citation_format', 'json')
    
    if not query:
        return JsonResponse({'error': 'query (q) parameter required'}, status=400)
    
    try:
        # Retrieve
        retriever = HybridRetriever()
        results = retriever.retrieve(query, top_k=top_k)
        
        # Build citations
        chunks_metadata = [
            {
                'file_path': chunk.document.file_path,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'repository': str(chunk.document.repository.name),
            }
            for chunk, _ in results
        ]
        
        citations = SourceAttributionBuilder.build_from_chunks(chunks_metadata)
        
        # Format citations
        if citation_format == 'markdown':
            formatted = CitationFormatter.format_markdown(citations)
        elif citation_format == 'html':
            formatted = CitationFormatter.format_html(citations)
        elif citation_format == 'bibtex':
            formatted = CitationFormatter.format_bibtex(citations)
        else:  # json
            formatted = CitationFormatter.format_json(citations)
        
        return JsonResponse({
            'query': query,
            'results_count': len(results),
            'citations': formatted,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def explain_query(request):
    """
    Explain query expansion and retrieval strategy.
    
    Query parameters:
        q: search query
    """
    query = request.GET.get('q')
    
    if not query:
        return JsonResponse({'error': 'query (q) parameter required'}, status=400)
    
    try:
        expander = QueryExpander()
        
        # Get expanded queries
        synonyms = expander.expand_with_synonyms(query)
        ngrams = expander.expand_with_ngrams(query, n=2)
        normalized = expander.normalize_query(query)
        
        # Get retrieval info
        retriever = HybridRetriever()
        results = retriever.retrieve(query, top_k=3)
        
        return JsonResponse({
            'original_query': query,
            'normalized_query': normalized,
            'synonym_variations': synonyms[:3],
            'ngram_variations': ngrams[:3],
            'retrieval_weights': {
                'bm25': retriever.weight_bm25,
                'vector': retriever.weight_vector,
            },
            'top_results': [
                {
                    'rank': i,
                    'file': results[i][0].document.file_path,
                    'score': results[i][1].get('hybrid_score', 0),
                }
                for i in range(min(3, len(results)))
            ],
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def compare_retrieval_strategies(request):
    """
    Compare BM25, vector, and hybrid retrieval strategies.
    
    Query parameters:
        q: search query
        top_k: number of results
    """
    query = request.GET.get('q')
    top_k = int(request.GET.get('top_k', 5))
    
    if not query:
        return JsonResponse({'error': 'query (q) parameter required'}, status=400)
    
    try:
        retriever = HybridRetriever()
        
        # Get all chunks for comparison
        from rag_api.core.models import Chunk
        all_chunks = Chunk.objects.select_related('document').all()
        
        if not all_chunks.exists():
            return JsonResponse({'error': 'No documents indexed'}, status=404)
        
        # Get results from each strategy
        results = retriever.retrieve(query, top_k=top_k)
        
        comparison = {
            'query': query,
            'strategies': {
                'bm25_weight': retriever.weight_bm25,
                'vector_weight': retriever.weight_vector,
            },
            'results': [
                {
                    'rank': i,
                    'file_path': chunk.document.file_path,
                    'bm25_score': metadata.get('bm25_score', 0),
                    'vector_score': metadata.get('vector_score', 0),
                    'hybrid_score': metadata.get('hybrid_score', 0),
                    'rerank_score': metadata.get('rerank_score', 0),
                }
                for i, (chunk, metadata) in enumerate(results, 1)
            ],
        }
        
        return JsonResponse(comparison)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_query_analytics(request):
    """
    Get analytics about past queries.
    
    Query parameters:
        limit: number of queries to return (default: 10)
        repository: filter by repository name
    """
    limit = int(request.GET.get('limit', 10))
    repository = request.GET.get('repository')
    
    try:
        queries = QueryLog.objects.all().order_by('-created_at')[:limit]
        
        analytics = {
            'total_queries': QueryLog.objects.count(),
            'queries': [
                {
                    'query': q.query_text,
                    'results_count': q.result_count,
                    'execution_time_ms': q.execution_time_ms,
                    'top_k': q.top_k,
                    'created_at': q.created_at.isoformat(),
                }
                for q in queries
            ],
        }
        
        # Add stats
        if queries.exists():
            avg_time = sum(q.execution_time_ms for q in queries) / len(queries)
            avg_results = sum(q.result_count for q in queries) / len(queries)
            
            analytics['stats'] = {
                'avg_execution_time_ms': avg_time,
                'avg_results_count': avg_results,
            }
        
        return JsonResponse(analytics)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def suggest_improvements(request):
    """
    Suggest improvements to query or retrieval settings.
    
    Query parameters:
        q: search query
    """
    query = request.GET.get('q')
    
    if not query:
        return JsonResponse({'error': 'query (q) parameter required'}, status=400)
    
    suggestions = []
    
    # Check query length
    if len(query) < 3:
        suggestions.append({
            'type': 'query_length',
            'message': 'Query is very short, consider being more specific',
            'severity': 'low',
        })
    
    # Check for special characters
    if any(c in query for c in ['*', '?', '[]', '{}']):
        suggestions.append({
            'type': 'special_chars',
            'message': 'Query contains special characters that might affect retrieval',
            'severity': 'medium',
        })
    
    # Check word count
    words = len(query.split())
    if words < 2:
        suggestions.append({
            'type': 'word_count',
            'message': 'Consider using more words to improve specificity',
            'severity': 'low',
        })
    elif words > 20:
        suggestions.append({
            'type': 'word_count',
            'message': 'Query is very long, consider simplifying',
            'severity': 'low',
        })
    
    # Check for stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    query_words = set(word.lower() for word in query.split())
    stopword_ratio = len(query_words & stopwords) / len(query_words) if query_words else 0
    
    if stopword_ratio > 0.5:
        suggestions.append({
            'type': 'stopwords',
            'message': 'Query has many stopwords, try removing them for better results',
            'severity': 'medium',
        })
    
    return JsonResponse({
        'query': query,
        'suggestions': suggestions,
    })
