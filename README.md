# VaulS.ai - Hybrid RAG Search Engine

**Production-ready AI search engine** for code and documentation repositories. Built with:
- **Frontend**: Vanilla JavaScript (zero dependencies)
- **Backend**: Vercel Functions (Node.js serverless)
- **Search**: Hybrid (BM25 full-text + Qdrant vector embeddings)
- **LLM**: Groq Mixtral 8x7b (streaming responses)
- **Database**: Vercel Postgres + Qdrant Cloud

🚀 **Deploy in 5 minutes** → See [QUICK_START.md](QUICK_START.md)

---

## Features

### 🔍 Intelligent Search
- **Hybrid retrieval**: Combines BM25 full-text search with semantic vector search
- **Streaming responses**: Real-time LLM answers via Groq API
- **Source attribution**: Automatic citations with line numbers
- **Multi-repository**: Search across unlimited repositories

### ⚡ Performance
- Serverless architecture (scales to millions of requests)
- Sub-second search latency (~400-800ms)
- Global edge caching via Vercel
- Optimized vector search with Qdrant

### 🎨 User Experience
- Beautiful vanilla JavaScript UI
- Dark mode (default) + Light mode
- Responsive mobile design
- Real-time streaming indicators
- Cookie-based authentication

### 🔒 Production Ready
- Authentication & sessions
- Health monitoring
- Comprehensive error handling
- API rate limiting support

---

## Quick Deploy

### Option 1: One-Click Deploy (Easiest)

1. Get API keys:
   - Groq: https://console.groq.com/keys
   - Qdrant: https://qdrant.tech

2. Deploy to Vercel:
   - Go to https://vercel.com/new
   - Import this GitHub repository
   - Add environment variables (GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY)
   - Click Deploy ✅

3. Your site is live in 2-3 minutes!

**See [QUICK_START.md](QUICK_START.md) for detailed steps**
