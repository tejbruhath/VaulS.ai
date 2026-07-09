# VaulS.ai - Hybrid RAG Pipeline

A production-ready Retrieval Augmented Generation (RAG) system combining BM25 sparse retrieval with dense vector search and cross-encoder re-ranking. Features semantic chunking, source attribution, and streaming SSE responses via a Django REST API backed by Qdrant and PostgreSQL.

## Quick Start

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your OpenAI API key

# 2. Start all services
docker-compose up -d

# 3. Initialize database
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# 4. Index a repository
curl -X POST http://localhost:8000/api/repositories/index/ \
  -H "Content-Type: application/json" \
  -d '{"owner":"vercel","name":"next.js","branch":"main"}'

# 5. Query with streaming
curl "http://localhost:8000/api/query/stream/?q=how%20do%20I%20use%20this"
```

See [README_RAG.md](README_RAG.md) for complete documentation.
