# VaulS.ai - Vercel Deployment Guide

## Overview

This is a modern Hybrid RAG pipeline running on Vercel serverless with:
- **Frontend**: Vanilla JavaScript
- **Backend**: Vercel Functions (Node.js)
- **Database**: Vercel Postgres + Qdrant Vector DB
- **LLM**: Groq API (Mixtral 8x7b)
- **Auth**: Cookie-based sessions

## Prerequisites

1. **Groq API Key** - Get from [console.groq.com](https://console.groq.com)
2. **Qdrant Cloud Account** - Create at [qdrant.tech](https://qdrant.tech)
3. **GitHub Account** - For deploying to Vercel
4. **Vercel Account** - Free tier available at [vercel.com](https://vercel.com)

## Setup Steps

### Step 1: Prepare Environment Variables

```bash
# Copy the environment template
cp .env.local.example .env.local

# Edit with your credentials
# Required:
# - GROQ_API_KEY: Your Groq API key
# - QDRANT_URL: Your Qdrant cloud instance URL
# - QDRANT_API_KEY: Your Qdrant API key
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Test Locally

```bash
npm run dev
# Open http://localhost:3000
```

### Step 4: Deploy to Vercel

#### Option A: Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables when prompted
# Or use:
vercel env add GROQ_API_KEY
vercel env add QDRANT_URL
vercel env add QDRANT_API_KEY
```

#### Option B: Via GitHub (Recommended)

1. Push code to GitHub repository
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your GitHub repository
4. Configure environment variables in project settings:
   - `GROQ_API_KEY`
   - `QDRANT_URL`
   - `QDRANT_API_KEY`
5. Click Deploy

### Step 5: Add Vercel Postgres

1. In Vercel project settings → "Storage"
2. Click "Create Database" → "Postgres"
3. Connect the database
4. Copy the connection string to environment variables

### Step 6: Initialize Database

```bash
curl https://your-domain.vercel.app/api/health

# This will trigger database initialization on first request
```

## Project Structure

```
.
├── pages/
│   ├── api/
│   │   ├── query.js           # Search endpoint (streaming)
│   │   ├── repositories.js    # Repository management
│   │   ├── health.js          # Health check
│   │   └── auth/
│   │       ├── login.js       # Login endpoint
│   │       └── logout.js      # Logout endpoint
│   └── index.js               # Next.js entry point
├── public/
│   ├── index.html             # Main UI
│   └── app.js                 # Vanilla JS app
├── styles/
│   └── globals.css            # Global styling
├── lib/
│   ├── db.js                  # PostgreSQL integration
│   ├── qdrant.js              # Qdrant vector search
│   ├── groq.js                # Groq LLM integration
│   └── auth.js                # Authentication
├── next.config.js
├── package.json
└── vercel.json
```

## API Endpoints

### Query Endpoint
- **POST** `/api/query`
- **Description**: Streaming search with hybrid retrieval
- **Request**: `{ query: string, limit?: number }`
- **Response**: Server-sent events (SSE) with streaming response

Example:
```bash
curl -X POST https://your-domain.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"how do I deploy to Vercel?"}'
```

### Repositories Endpoint
- **GET** `/api/repositories` - List all indexed repositories
- **POST** `/api/repositories` - Add new repository
- **Auth**: Required for POST

### Health Check
- **GET** `/api/health`
- **Description**: System status and service availability

### Authentication
- **POST** `/api/auth/login` - User login
- **POST** `/api/auth/logout` - User logout

## Performance Optimization

### 1. Database Indexing
The database includes indices for fast full-text search:
```sql
CREATE INDEX idx_bm25_text ON bm25_index USING GIN (text_vector);
```

### 2. Caching
- Use Vercel's automatic edge caching for static files
- Set cache headers in API responses

### 3. Function Memory
- Adjusted to 1024MB for better performance
- Max duration: 60 seconds per request

### 4. Vector Search
- Qdrant handles vector search efficiently
- Cosine similarity with 384-dimensional embeddings
- Score threshold: 0.6 for quality results

## Deployment Checklist

- [ ] Environment variables set (GROQ_API_KEY, QDRANT_*)
- [ ] Vercel Postgres connected and initialized
- [ ] Qdrant Cloud instance running
- [ ] GitHub repository created and connected to Vercel
- [ ] Domain configured (optional)
- [ ] Health check passing at `/api/health`
- [ ] Search working end-to-end
- [ ] Authentication working
- [ ] Repository indexing working

## Troubleshooting

### Database Connection Failed
- Check `POSTGRES_PRISMA_URL` environment variable
- Ensure Vercel Postgres is connected
- Check database exists and migrations ran

### Qdrant Search Not Working
- Verify `QDRANT_URL` and `QDRANT_API_KEY`
- Check Qdrant instance is running
- Run health check: `GET /api/health`

### Groq API Errors
- Verify `GROQ_API_KEY` is valid
- Check API rate limits
- Ensure API account is active

### Streaming Not Working
- Check browser supports Server-Sent Events
- Verify CORS headers are set correctly
- Check network tab in browser DevTools

## Monitoring

### Vercel Dashboard
- Monitor function duration
- View error logs
- Track deployments

### Custom Monitoring
```bash
# Check health periodically
curl https://your-domain.vercel.app/api/health | jq .
```

## Cost Estimates

- **Vercel**: Free tier (Function calls, Storage)
- **Groq API**: Free tier available
- **Qdrant Cloud**: Free tier (1GB storage)
- **Postgres**: 1GB free with Vercel

## Production Deployment Best Practices

1. **Environment Secrets**
   - Use Vercel Secrets management
   - Never commit `.env.local`
   - Rotate API keys regularly

2. **Monitoring & Alerts**
   - Set up error tracking
   - Monitor API latency
   - Alert on health check failures

3. **Rate Limiting**
   - Implement query rate limits
   - Use Vercel middleware for auth

4. **Database**
   - Enable automated backups
   - Monitor connection pool
   - Optimize slow queries

5. **Security**
   - Enable HTTPS (automatic with Vercel)
   - Set secure CORS policies
   - Validate all inputs

## Next Steps

1. Index your first GitHub repository
2. Test search functionality
3. Customize styling in `public/index.html`
4. Add more repositories
5. Monitor performance and optimize

## Support

- Vercel Docs: https://vercel.com/docs
- Groq API: https://console.groq.com/docs
- Qdrant: https://qdrant.tech/documentation
- PostgreSQL: https://www.postgresql.org/docs/

## License

MIT - See LICENSE file for details
