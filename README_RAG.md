# Hybrid RAG Pipeline

A production-ready Retrieval Augmented Generation (RAG) system that combines BM25 sparse retrieval with dense vector search and cross-encoder re-ranking. Built with Django REST API, backed by Qdrant and PostgreSQL.

## Architecture

```
┌─────────────────┐
│  GitHub Repos   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Semantic Chunking          │  (512 tokens, 100 overlap)
│  - Markdown sections        │
│  - Code functions/classes   │
└────────┬────────────────────┘
         │
         ├────────────────────────┐
         ▼                        ▼
    ┌─────────────┐      ┌──────────────────┐
    │ PostgreSQL  │      │  Qdrant Vectors  │
    │ - Chunks    │      │  - Embeddings    │
    │ - Metadata  │      │  - BM25 tokens   │
    └─────────────┘      └──────────────────┘
         ▲                        ▲
         │                        │
         └─────────────┬──────────┘
                       │
                ┌──────▼──────┐
                │   Query     │
                └──────┬──────┘
                       │
         ┌─────────────┴──────────────┐
         ▼                            ▼
    ┌──────────────┐         ┌──────────────────┐
    │  BM25 Sparse │         │  Vector Dense    │
    │  Retrieval   │         │  Retrieval       │
    └──────────────┘         └──────────────────┘
         │ (0.3 weight)           │ (0.7 weight)
         └─────────────┬──────────┘
                       ▼
            ┌──────────────────────┐
            │ Hybrid Score Ranking │
            └──────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Cross-Encoder Re-rank│  (top 10 → top 5)
            └──────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  LLM Generation      │
            │  (GPT-4 Turbo)       │
            │  + Source Citation   │
            └──────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Streaming SSE API   │
            │  (Real-time events)  │
            └──────────────────────┘
```

## Features

- **Hybrid Search**: Combines BM25 (sparse) and dense vector search for comprehensive retrieval
- **Semantic Chunking**: Intelligent document splitting based on markdown sections and code structure
- **Cross-Encoder Re-ranking**: Neural re-ranking for improved relevance
- **Source Attribution**: Precise source tracking with file paths and line numbers
- **Streaming Responses**: Server-sent events (SSE) for real-time streaming LLM responses
- **Batch Indexing**: Celery-based async tasks for efficient repository indexing
- **Production Ready**: Docker Compose setup with all required services

## Technology Stack

### Core
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL (metadata & BM25 index)
- **Vector DB**: Qdrant (dense embeddings)
- **Task Queue**: Celery + Redis
- **LLM**: OpenAI GPT-4 Turbo
- **Embeddings**: OpenAI text-embedding-3-small

### Libraries
- **Retrieval**: rank-bm25, sentence-transformers
- **GitHub**: PyGithub
- **APIs**: FastAPI (optional for streaming), Django-rest-framework

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/rag-pipeline.git
cd rag-pipeline
```

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env with your API keys
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..." # Optional, for private repos
```

### 3. Start Services
```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Qdrant (port 6333)
- Django API (port 8000)
- Celery Worker
- Celery Beat (scheduler)

### 4. Initialize Database
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## API Usage

### 1. Index a Repository
```bash
curl -X POST http://localhost:8000/api/repositories/index/ \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "vercel",
    "name": "next.js",
    "branch": "main"
  }'
```

### 2. Query with Streaming
```bash
curl -X GET "http://localhost:8000/api/query/stream/?q=how%20do%20I%20use%20this&top_k=5"
```

Response (Server-Sent Events):
```
data: {"type":"retrieval","rank":1,"file_path":"docs/guide.md",...}

data: {"type":"response","content":"Based on the sources"}

data: {"type":"complete","retrieval_time_ms":245,"sources_count":5}
```

### 3. Get Repository Stats
```bash
curl http://localhost:8000/api/repositories/stats/
```

### 4. List Indexed Documents
```bash
curl http://localhost:8000/api/documents/
```

### 5. List Chunks
```bash
curl http://localhost:8000/api/chunks/?document_id=<uuid>
```

### 6. Health Check
```bash
curl http://localhost:8000/api/health/
```

## Configuration

Edit `.env` file to customize:

```env
# Hybrid search weights (must sum to 1.0)
HYBRID_WEIGHT_BM25=0.3      # Sparse retrieval weight
HYBRID_WEIGHT_VECTOR=0.7    # Dense retrieval weight

# Chunking parameters
CHUNK_SIZE=512              # Tokens per chunk
CHUNK_OVERLAP=100           # Overlap tokens

# Re-ranking
RERANK_TOP_K=10             # Candidates for re-ranking
FINAL_TOP_K=5               # Final results

# Models
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4-turbo-preview
```

## Development

### Local Setup (without Docker)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL locally and create database
createdb rag_db

# Start Redis
redis-server

# Start Qdrant
qdrant

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# In separate terminal, start Celery worker
celery -A config worker -l info
```

### Admin Interface
Access the Django admin at `http://localhost:8000/admin/` with your superuser credentials to:
- View indexed repositories and documents
- Monitor queries and results
- Manage BM25 index statistics

## Deployment

### Docker Production Build
```bash
# Build image
docker build -t rag-api:latest .

# Push to registry
docker tag rag-api:latest myregistry/rag-api:latest
docker push myregistry/rag-api:latest
```

### Kubernetes Deployment
See `k8s/` directory for example manifests.

### Environment Variables for Production
```env
DEBUG=False
DJANGO_SECRET_KEY=<generate-random-key>
ALLOWED_HOSTS=api.example.com,www.example.com
DB_HOST=<postgres-host>
QDRANT_URL=<qdrant-host>
OPENAI_API_KEY=<your-key>
```

## Performance Optimization

### Indexing Speed
- Batch embedding requests (handled automatically)
- Use Celery for parallel document processing
- Rebuild BM25 index during off-peak hours

### Query Latency
- Vector search: ~50-100ms (Qdrant)
- BM25 search: ~10-30ms
- Re-ranking: ~50-100ms
- LLM generation: ~1-3s

### Memory Management
- Redis caching for BM25 index
- Qdrant memory-mapped storage
- PostgreSQL connection pooling

## Troubleshooting

### Qdrant Connection Error
```bash
# Check if Qdrant is running
curl http://localhost:6333/health

# Restart Qdrant
docker-compose restart qdrant
```

### PostgreSQL Connection Error
```bash
# Check database
docker-compose exec postgres psql -U postgres -d rag_db -c "SELECT COUNT(*) FROM core_document;"

# Reset database
docker-compose exec postgres dropdb -U postgres rag_db
docker-compose exec web python manage.py migrate
```

### Out of Memory
- Reduce CHUNK_SIZE
- Reduce RERANK_TOP_K
- Process repositories in smaller batches

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
