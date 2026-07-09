# RAG API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently unauthenticated. Add authentication in production via Django-REST-Framework auth classes.

## Endpoints

### Repositories

#### List Repositories
```
GET /api/repositories/
```

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "owner": "vercel",
      "name": "next.js",
      "url": "https://github.com/vercel/next.js",
      "branch": "main",
      "last_indexed": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Create Repository
```
POST /api/repositories/
```

**Body:**
```json
{
  "owner": "vercel",
  "name": "next.js",
  "url": "https://github.com/vercel/next.js",
  "branch": "main"
}
```

#### Index Repository (Async)
```
POST /api/repositories/index/
```

**Body:**
```json
{
  "owner": "vercel",
  "name": "next.js",
  "branch": "main"
}
```

**Response (202 Accepted):**
```json
{
  "status": "indexing_started",
  "task_id": "abc123def456",
  "owner": "vercel",
  "name": "next.js"
}
```

#### Get Repository Statistics
```
GET /api/repositories/stats/
```

**Response:**
```json
{
  "repositories": 2,
  "documents": 145,
  "chunks": 892
}
```

#### Rebuild BM25 Index
```
POST /api/repositories/rebuild_index/
```

**Response:**
```json
{
  "status": "rebuilding",
  "task_id": "xyz789"
}
```

### Documents

#### List Documents
```
GET /api/documents/
```

**Query Parameters:**
- `repository_id` (optional): Filter by repository ID

**Response:**
```json
{
  "count": 145,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "repository": "550e8400-e29b-41d4-a716-446655440000",
      "repository_display": "vercel/next.js",
      "file_path": "docs/getting-started.md",
      "file_type": "md",
      "created_at": "2024-01-15T09:30:00Z",
      "updated_at": "2024-01-15T09:30:00Z"
    }
  ]
}
```

### Chunks

#### List Chunks
```
GET /api/chunks/
```

**Query Parameters:**
- `document_id` (optional): Filter by document ID

**Response:**
```json
{
  "count": 892,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "document_id": "550e8400-e29b-41d4-a716-446655440001",
      "document_file_path": "docs/getting-started.md",
      "content": "# Getting Started\n\nThis guide...",
      "chunk_index": 0,
      "start_line": 1,
      "end_line": 50,
      "token_count": 245,
      "created_at": "2024-01-15T09:35:00Z"
    }
  ]
}
```

### Query Stream (Hybrid RAG)

#### Query with Streaming SSE Response
```
GET /api/query/stream/?q=<query>&top_k=<int>&stream=<bool>
```

**Query Parameters:**
- `q` (required): Search query
- `top_k` (optional, default=5): Number of results
- `stream` (optional, default=true): Enable streaming

**Response (200 OK with text/event-stream):**

The response is a stream of Server-Sent Events (SSE). Each event is a JSON object with a `type` field:

##### Retrieval Event
```json
{
  "type": "retrieval",
  "rank": 1,
  "chunk_id": "550e8400-e29b-41d4-a716-446655440002",
  "file_path": "docs/getting-started.md",
  "content": "# Getting Started\n\nThis guide explains...",
  "scores": {
    "bm25": 0.45,
    "vector": 0.89,
    "hybrid": 0.74,
    "rerank": 0.92
  }
}
```

##### Response Event
```json
{
  "type": "response",
  "content": "Based on the sources"
}
```

(Multiple response events are sent as the LLM generates text)

##### Complete Event
```json
{
  "type": "complete",
  "query": "how do I use this",
  "retrieval_time_ms": 245,
  "sources_count": 5
}
```

##### Error Event
```json
{
  "type": "error",
  "error": "OpenAI API key not configured"
}
```

### Health Check

#### Health Check
```
GET /api/health/
```

**Response:**
```json
{
  "status": "healthy",
  "documents": 145,
  "chunks": 892,
  "queries_logged": 42
}
```

## Score Explanations

### BM25 Score
- **Range:** 0.0 - ~10.0 (unbounded, depends on document length)
- **What it measures:** Keyword matching relevance using BM25 algorithm
- **Good for:** Exact term matches, technical documentation

### Vector Score
- **Range:** 0.0 - 1.0 (cosine similarity)
- **What it measures:** Semantic similarity between query and document
- **Good for:** Conceptual similarity, synonyms

### Hybrid Score
- **Range:** 0.0 - 1.0 (normalized combination)
- **Calculation:** `0.3 * normalized_bm25 + 0.7 * vector_score`
- **Default weights:** Can be configured in `.env`

### Rerank Score
- **Range:** -1.0 - 1.0 (cosine similarity)
- **What it measures:** Neural re-ranking based on query relevance
- **Why used:** Provides final ranking with deep semantic understanding

## Error Handling

### 400 Bad Request
```json
{
  "error": "query (q) parameter is required"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Server Error
```json
{
  "error": "Internal server error message"
}
```

## Rate Limiting

No rate limiting currently implemented. Add in production using Django-REST-Framework throttling.

## Pagination

Endpoints that return lists support pagination:

```
GET /api/documents/?page=2&page_size=20
```

Default page size: 10

## Examples

### Python Client
```python
from scripts.rag_client import RAGClient

client = RAGClient()

# Index a repository
result = client.index_repository("vercel", "next.js")

# Query with streaming
for event in client.query_stream("how do I setup Next.js"):
    if event['type'] == 'retrieval':
        print(f"Found: {event['file_path']}")
    elif event['type'] == 'response':
        print(event['content'], end='')
```

### cURL
```bash
# Index repository
curl -X POST http://localhost:8000/api/repositories/index/ \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "vercel",
    "name": "next.js",
    "branch": "main"
  }'

# Query with streaming
curl -N "http://localhost:8000/api/query/stream/?q=how%20to%20deploy&top_k=3"
```

### JavaScript/Node.js
```javascript
// Query with streaming
const response = await fetch(
  'http://localhost:8000/api/query/stream/?q=how%20to%20deploy&top_k=5'
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      if (event.type === 'response') {
        process.stdout.write(event.content);
      }
    }
  }
}
```

## Performance Tips

1. **Batch Indexing**: Use Celery tasks for large repositories
2. **Query Caching**: Consider caching popular queries
3. **Connection Pooling**: Use database connection pooling in production
4. **Embedding Batching**: Batch embedding requests when possible
5. **Vector Search Optimization**: Use Qdrant's indexing options for faster searches

## Monitoring

View detailed logs in Django admin:
- Query logs at `/admin/core/querylog/`
- Query results at `/admin/core/queryresult/`
- Index statistics at `/admin/core/bm25index/`
