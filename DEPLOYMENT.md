# Deployment Guide

## Local Development

### Quick Start with Docker Compose

```bash
# 1. Copy environment
cp .env.example .env
export OPENAI_API_KEY=sk-...

# 2. Start all services
docker-compose up -d

# 3. Initialize database
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# 4. Access services
- API: http://localhost:8000
- Admin: http://localhost:8000/admin
- Qdrant: http://localhost:6333
```

### Development without Docker

```bash
# Setup venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis locally
# Start Qdrant locally

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver

# In another terminal, start Celery worker
celery -A config worker -l info
```

## Production Deployment

### AWS ECS Deployment

1. **Build and push Docker image:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t rag-api:latest .
docker tag rag-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/rag-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/rag-api:latest
```

2. **Create RDS PostgreSQL database:**
   - Engine: PostgreSQL 15
   - Multi-AZ: Enabled
   - Backup retention: 30 days

3. **Create ElastiCache Redis cluster:**
   - Engine: Redis 7.0
   - Multi-AZ: Enabled
   - Automatic failover: Enabled

4. **Deploy Qdrant:**
   - Use managed Qdrant Cloud or self-hosted on EC2
   - Enable backups and snapshots

5. **Create ECS task definition:**
```json
{
  "family": "rag-api",
  "containerDefinitions": [
    {
      "name": "rag-api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/rag-api:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DEBUG", "value": "False"},
        {"name": "DB_HOST", "value": "rds-endpoint"},
        {"name": "CELERY_BROKER_URL", "value": "redis://elasticache-endpoint:6379/0"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-api",
          "awslogs-region": "us-east-1"
        }
      }
    }
  ]
}
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

```bash
# Deploy
kubectl apply -f k8s/

# Check status
kubectl get pods -n rag

# View logs
kubectl logs -n rag -l app=rag-api -f
```

### Environment Variables for Production

```env
# Django
DEBUG=False
DJANGO_SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=api.example.com

# Database
DB_HOST=postgres.example.com
DB_NAME=rag_db
DB_USER=postgres
DB_PASSWORD=<secure-password>
DB_PORT=5432

# Cache & Queue
CELERY_BROKER_URL=redis://redis.example.com:6379/0
CELERY_RESULT_BACKEND=redis://redis.example.com:6379/1

# Vector Database
QDRANT_URL=http://qdrant.example.com:6333
QDRANT_API_KEY=<api-key>

# AI APIs
OPENAI_API_KEY=sk-<your-key>
GITHUB_TOKEN=ghp_<your-token>

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Performance Optimization

### Database Optimization

```sql
-- Create indices for common queries
CREATE INDEX idx_chunk_document ON core_chunk(document_id, chunk_index);
CREATE INDEX idx_document_repository ON core_document(repository_id, file_path);
CREATE INDEX idx_querylog_created ON core_querylog(created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM core_chunk WHERE document_id = '...';

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Caching Strategy

```python
# Cache configuration in settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        }
    }
}
```

### Vector Search Optimization

- **Qdrant Configuration:**
  - Use HNSW indexing for 1M+ vectors
  - Enable mmap storage for memory efficiency
  - Configure segment size: 512MB

```yaml
# qdrant config
storage:
  snapshots_path: ./snapshots
  delta_path: ./deltas

hnsw_config:
  m: 16
  ef_construct: 200
  ef: 100
  seed: 0
```

### API Optimization

- **Use connection pooling:**
```python
# postgres connection pool
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pool timeout
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

- **Enable query result caching:**
```python
HYBRID_RETRIEVAL_CACHE_TTL = 3600  # 1 hour
```

- **Use async tasks for heavy operations:**
```python
# Long-running indexing in background
from celery import shared_task
@shared_task
def index_large_repo(owner, name):
    # Processing happens in background
    pass
```

### Monitoring and Logging

```python
# Set up structured logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/rag-api.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'rag_api': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}
```

## Monitoring Checklist

- [ ] Application performance metrics (APM) configured
- [ ] Log aggregation set up (ELK, CloudWatch, etc.)
- [ ] Alerts configured for:
  - High error rates
  - Slow queries (> 5s)
  - High memory usage
  - Database connection pool exhaustion
  - Qdrant disk space
- [ ] Backup and recovery tested
- [ ] Rate limiting configured
- [ ] DDoS protection enabled

## Security Checklist

- [ ] HTTPS enabled
- [ ] CSRF protection enabled
- [ ] XSS protection headers set
- [ ] API rate limiting configured
- [ ] Authentication implemented
- [ ] SQL injection prevention verified
- [ ] Secrets stored in environment variables
- [ ] Database credentials rotated
- [ ] API keys rotated regularly
- [ ] Firewall rules configured
- [ ] VPC security groups configured

## Scaling Strategy

### Horizontal Scaling

1. **API Workers:** Scale API instances behind load balancer
2. **Celery Workers:** Add more workers for background tasks
3. **Database:** Read replicas for read-heavy queries
4. **Vector DB:** Qdrant clustering or replication

### Vertical Scaling

- Increase instance size for higher throughput
- Allocate more memory for larger datasets
- Use faster CPU for embedding generation

### Database Sharding

For very large scale (billions of vectors):
- Shard by repository
- Shard by document type
- Geographic distribution

## Disaster Recovery

### Backup Strategy

```bash
# Daily database backups
0 2 * * * pg_dump rag_db | gzip > /backups/rag_db_$(date +%Y%m%d).sql.gz

# Qdrant snapshots
0 3 * * * curl -X POST http://localhost:6333/collections/documents/snapshots

# Store backups in S3
aws s3 sync /backups s3://rag-backups/
```

### Recovery Procedure

1. Restore PostgreSQL from backup
2. Restore Qdrant collection from snapshot
3. Verify data integrity
4. Restart services

## Cost Optimization

- Use spot instances for development
- Right-size instances based on actual usage
- Enable auto-scaling based on metrics
- Use S3 for log archival
- Consider reserved instances for production

## Maintenance

### Regular Tasks

- [ ] Monitor log files for errors
- [ ] Review and optimize slow queries
- [ ] Update dependencies monthly
- [ ] Review security patches
- [ ] Clean up old query logs
- [ ] Optimize database indices
- [ ] Rotate API keys

### Upgrade Procedure

1. Test in staging environment
2. Create database backup
3. Deploy new version
4. Verify functionality
5. Monitor metrics for anomalies
