#!/usr/bin/env python
"""Python client for RAG API."""
import requests
import json
from typing import Generator, Dict


class RAGClient:
    """Client for interacting with RAG API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def index_repository(self, owner: str, name: str, branch: str = "main") -> Dict:
        """Index a GitHub repository."""
        response = self.session.post(
            f"{self.base_url}/api/repositories/index/",
            json={"owner": owner, "name": name, "branch": branch}
        )
        return response.json()
    
    def query_stream(self, query: str, top_k: int = 5) -> Generator[Dict, None, None]:
        """
        Query with streaming SSE responses.
        
        Yields:
            Dictionary events with type, content, and metadata
        """
        response = self.session.get(
            f"{self.base_url}/api/query/stream/",
            params={"q": query, "top_k": top_k},
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    yield data
    
    def get_repositories(self) -> Dict:
        """Get all indexed repositories."""
        response = self.session.get(f"{self.base_url}/api/repositories/")
        return response.json()
    
    def get_documents(self, repository_id: str = None) -> Dict:
        """Get indexed documents."""
        params = {}
        if repository_id:
            params['repository_id'] = repository_id
        response = self.session.get(f"{self.base_url}/api/documents/", params=params)
        return response.json()
    
    def get_chunks(self, document_id: str = None) -> Dict:
        """Get document chunks."""
        params = {}
        if document_id:
            params['document_id'] = document_id
        response = self.session.get(f"{self.base_url}/api/chunks/", params=params)
        return response.json()
    
    def get_stats(self) -> Dict:
        """Get indexing statistics."""
        response = self.session.get(f"{self.base_url}/api/repositories/stats/")
        return response.json()
    
    def health_check(self) -> Dict:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/api/health/")
        return response.json()


def main():
    """Example usage."""
    client = RAGClient()
    
    # Check health
    print("Health check:")
    print(client.health_check())
    print()
    
    # Query with streaming
    print("Query: 'how do I use this'")
    print("-" * 50)
    
    for event in client.query_stream("how do I use this", top_k=3):
        event_type = event.get('type')
        
        if event_type == 'retrieval':
            print(f"\n[RETRIEVED] Rank {event['rank']}: {event['file_path']}")
            print(f"  Scores: BM25={event['scores']['bm25']:.3f}, "
                  f"Vector={event['scores']['vector']:.3f}, "
                  f"Rerank={event['scores']['rerank']:.3f}")
        
        elif event_type == 'response':
            print(event['content'], end='', flush=True)
        
        elif event_type == 'complete':
            print(f"\n\n[COMPLETE] Retrieval time: {event['retrieval_time_ms']}ms")
        
        elif event_type == 'error':
            print(f"[ERROR] {event['error']}")


if __name__ == '__main__':
    main()
