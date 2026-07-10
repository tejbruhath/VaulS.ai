## 🚀 VaulS.ai - 5-Minute Quick Start

Your Hybrid RAG pipeline is ready for deployment on Vercel. Follow these steps:

### Prerequisites
- Groq API key (free at https://console.groq.com)
- Qdrant Cloud account (free at https://qdrant.tech)
- GitHub account (for version control)
- Vercel account (free at https://vercel.com)

### Step 1: Get Your API Keys

**Groq API Key:**
1. Visit https://console.groq.com/keys
2. Create new API key
3. Copy the key

**Qdrant Cloud:**
1. Sign up at https://qdrant.tech
2. Create new cluster
3. Copy URL and API key

### Step 2: Deploy to Vercel

**Option A: One-Click Deploy (Recommended)**

1. Go to your GitHub repository
2. Visit https://vercel.com/new
3. Select "Import from GitHub"
4. Choose your VaulS.ai repository
5. In Environment Variables, add:
   - `GROQ_API_KEY`: Your Groq API key
   - `QDRANT_URL`: Your Qdrant cloud URL
   - `QDRANT_API_KEY`: Your Qdrant API key
6. Click "Deploy"

**Option B: Via CLI**

```bash
# Install Vercel CLI
npm i -g vercel

# Set environment variables
vercel env add GROQ_API_KEY
vercel env add QDRANT_URL
vercel env add QDRANT_API_KEY

# Deploy
vercel

# View your live site
vercel list
```

### Step 3: Add Vercel Postgres (Optional but Recommended)

1. Go to your Vercel project dashboard
2. Click "Storage" tab
3. Create new Postgres database
4. Connection string is auto-configured

### Step 4: Test Your Deployment

```bash
# Check if API is working
curl https://your-domain.vercel.app/api/health

# Try a search
curl -X POST https://your-domain.vercel.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"how to deploy"}'
```

### Step 5: Index Your First Repository

In the web UI:
1. Click "+ Add Repository"
2. Enter owner, repository name, and branch
3. Click "Index Repository"
4. Wait for indexing to complete
5. Try searching!

---

## Project Structure

```
Vercel Deployment:
├── Frontend
│   └── public/index.html          # Vanilla JS UI
│       + app.js                    # Client-side logic
│       + styles/globals.css        # Styling
│
├── Backend (Vercel Functions)
│   ├── /api/query.js              # Search endpoint (streaming)
│   ├── /api/repositories.js       # Repository management
│   ├── /api/health.js             # Health check
│   └── /api/auth/
│       ├── login.js
│       └── logout.js
│
├── Database Layer
│   ├── lib/db.js                  # Vercel Postgres
│   ├── lib/qdrant.js              # Qdrant vector search
│   ├── lib/groq.js                # Groq LLM API
│   └── lib/auth.js                # Authentication
```

## API Endpoints (Live)

Once deployed, you have:

- **Query**: `POST /api/query` - Search with streaming responses
- **Repos**: `GET/POST /api/repositories` - Manage indexed repos
- **Health**: `GET /api/health` - System status
- **Auth**: `POST /api/auth/login` - User login

## Features

✅ **Hybrid Search**
- BM25 full-text search (PostgreSQL)
- Vector semantic search (Qdrant)
- Combined ranked results

✅ **Streaming Responses**
- Real-time LLM streaming via Groq
- Server-sent events (SSE)
- Progressive rendering

✅ **Source Attribution**
- Automatic citations
- Line number tracking
- Repository references

✅ **Authentication**
- Cookie-based sessions
- Login/logout support

✅ **Performance**
- Serverless scalability
- Global edge caching
- Optimized vector search

## Customization

### Change Default Prompt
Edit `lib/groq.js` - update `defaultSystemPrompt`

### Adjust Search Weights
Edit `pages/api/query.js` - modify BM25/vector ratio

### Customize UI
Edit `public/index.html` and `styles/globals.css`

### Change LLM Model
Edit `lib/groq.js` - change `model: 'mixtral-8x7b-32768'`

## Monitoring

Check deployment health:
```bash
# View logs
vercel logs

# Check function usage
vercel analytics

# Monitor database
# (In Vercel dashboard → Storage → Postgres)
```

## Troubleshooting

**Deployment fails:**
- Check all environment variables are set
- Verify GitHub repository is connected
- Check logs in Vercel dashboard

**Searches return no results:**
- Add some repositories for indexing
- Wait for indexing to complete
- Check health endpoint: `/api/health`

**LLM not responding:**
- Verify GROQ_API_KEY is valid
- Check API rate limits
- Review error logs

**Vector search not working:**
- Verify Qdrant URL and API key
- Check Qdrant cluster is running
- Review API response in network tab

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Index your repositories
3. ✅ Test search functionality
4. 🔄 Customize styling and prompts
5. 🔄 Add more repositories
6. 🔄 Set up monitoring and alerts

## Cost Breakdown (Monthly)

- **Vercel**: Free tier covers most use cases
  - Functions: 1M invocations free
  - Storage: 1GB Postgres free
  
- **Groq**: Free API tier
  - Up to rate limits included
  
- **Qdrant**: Free cloud tier
  - 1GB storage free
  - Great for prototyping

**Total: $0-50/month for hobby projects**

## Get Help

- Vercel Docs: https://vercel.com/docs
- Groq Docs: https://console.groq.com/docs
- Qdrant Docs: https://qdrant.tech/documentation
- This project: https://github.com/tejbruhath/VaulS.ai

---

**🎉 Your RAG search engine is now live on the internet!**

Start indexing repositories and searching through your codebase instantly.
