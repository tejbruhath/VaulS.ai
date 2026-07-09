"""Streaming response utilities."""
import json
from typing import Generator, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StreamingEventBuffer:
    """Buffer and format streaming events."""
    
    def __init__(self):
        self.events = []
    
    def add_event(self, event_type: str, data: Dict) -> None:
        """Add an event to buffer."""
        event = {
            'type': event_type,
            **data
        }
        self.events.append(event)
    
    def get_sse_line(self, event: Dict) -> str:
        """Format event as SSE line."""
        return f"data: {json.dumps(event)}\n\n"
    
    def flush_as_sse(self) -> Generator[str, None, None]:
        """Yield all events as SSE format."""
        for event in self.events:
            yield self.get_sse_line(event)


class StreamingResponseBuilder:
    """Build streaming responses with proper formatting."""
    
    @staticmethod
    def create_retrieval_event(rank: int, chunk: 'Chunk', scores: Dict) -> Dict:
        """Create retrieval event."""
        return {
            'rank': rank,
            'chunk_id': str(chunk.id),
            'file_path': chunk.document.file_path,
            'repository': str(chunk.document.repository.id),
            'content': chunk.content[:500] + '...' if len(chunk.content) > 500 else chunk.content,
            'start_line': chunk.start_line,
            'end_line': chunk.end_line,
            'scores': {
                'bm25': scores.get('bm25_score', 0),
                'vector': scores.get('vector_score', 0),
                'hybrid': scores.get('hybrid_score', 0),
                'rerank': scores.get('rerank_score', 0),
            },
        }
    
    @staticmethod
    def create_response_event(content: str) -> Dict:
        """Create response text event."""
        return {
            'content': content,
            'timestamp': None,  # Will be set by consumer
        }
    
    @staticmethod
    def create_complete_event(query: str, retrieval_time_ms: int, 
                            sources_count: int) -> Dict:
        """Create completion event."""
        return {
            'query': query,
            'retrieval_time_ms': retrieval_time_ms,
            'sources_count': sources_count,
            'status': 'completed',
        }
    
    @staticmethod
    def create_error_event(error: str, error_type: str = 'general') -> Dict:
        """Create error event."""
        return {
            'error': error,
            'error_type': error_type,
            'status': 'failed',
        }
    
    @staticmethod
    def create_metadata_event(metadata: Dict) -> Dict:
        """Create metadata event."""
        return {
            'metadata': metadata,
        }


class StreamingErrorHandler:
    """Handle errors in streaming responses."""
    
    @staticmethod
    def handle_retrieval_error(error: Exception, query: str) -> Generator[str, None, None]:
        """Handle retrieval errors."""
        logger.error(f"Retrieval failed for query '{query}': {str(error)}")
        
        error_event = StreamingResponseBuilder.create_error_event(
            f"Retrieval failed: {str(error)}",
            error_type='retrieval_error'
        )
        yield f"data: {json.dumps({'type': 'error', **error_event})}\n\n"
    
    @staticmethod
    def handle_llm_error(error: Exception, query: str) -> Generator[str, None, None]:
        """Handle LLM generation errors."""
        logger.error(f"LLM generation failed for query '{query}': {str(error)}")
        
        error_event = StreamingResponseBuilder.create_error_event(
            f"Generation failed: {str(error)}",
            error_type='llm_error'
        )
        yield f"data: {json.dumps({'type': 'error', **error_event})}\n\n"
    
    @staticmethod
    def create_fallback_response(query: str, citations: list) -> Generator[str, None, None]:
        """Create fallback response when LLM generation fails."""
        # Send metadata about fallback
        fallback_event = {
            'type': 'fallback',
            'message': 'LLM generation unavailable, returning raw search results',
            'query': query,
            'sources_count': len(citations),
        }
        yield f"data: {json.dumps(fallback_event)}\n\n"
        
        # Stream search results
        for i, citation in enumerate(citations, 1):
            result_event = {
                'type': 'search_result',
                'rank': i,
                'file_path': citation.file_path,
                'lines': f"{citation.start_line}-{citation.end_line}",
            }
            yield f"data: {json.dumps(result_event)}\n\n"
