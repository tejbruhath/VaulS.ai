import { searchChunks, queryDatabase } from '../../lib/db';
import { generateResponseStream, embedText } from '../../lib/groq';
import { searchVectors } from '../../lib/qdrant';
import { getUserId } from '../../lib/auth';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { query, limit = 5 } = req.body;
  const userId = getUserId(req);

  if (!query || query.trim().length === 0) {
    return res.status(400).json({ error: 'Query is required' });
  }

  try {
    // Log the query
    await queryDatabase(
      `INSERT INTO query_logs (query, user_id) VALUES ($1, $2)`,
      [query, userId]
    );

    // Hybrid search: BM25 + Vector
    const bm25Results = await searchChunks(query, limit);
    let vectorResults = [];

    try {
      const queryEmbedding = await embedText(query);
      vectorResults = await searchVectors(queryEmbedding, limit);
    } catch (e) {
      console.warn('Vector search failed, using BM25 only:', e.message);
    }

    // Combine and deduplicate results
    const allResults = [...bm25Results, ...vectorResults];
    const uniqueResults = Array.from(
      new Map(allResults.map(item => [item.id, item])).values()
    ).slice(0, limit);

    // Build context for LLM
    const context = uniqueResults
      .map((result, idx) => 
        `[${idx + 1}] From ${result.owner}/${result.name} (${result.file_path}:${result.start_line}-${result.end_line}):\n${result.content}`
      )
      .join('\n\n---\n\n');

    if (context.length === 0) {
      return res.status(200).json({
        response: 'I could not find relevant information in the indexed repositories to answer your question.',
        sources: [],
      });
    }

    // Stream the response
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    let fullResponse = '';

    try {
      const stream = await generateResponseStream(query, context);

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || '';
        if (content) {
          fullResponse += content;
          res.write(`data: ${JSON.stringify({ delta: content })}\n\n`);
        }
      }
    } catch (streamError) {
      console.error('Stream error:', streamError);
      res.write(`data: ${JSON.stringify({ error: 'Stream failed' })}\n\n`);
    }

    // Send sources at the end
    res.write(`data: ${JSON.stringify({ 
      sources: uniqueResults.map(r => ({
        file: r.file_path,
        repository: `${r.owner}/${r.name}`,
        lines: `${r.start_line}-${r.end_line}`,
      })),
      done: true,
    })}\n\n`);

    res.end();
  } catch (error) {
    console.error('Query error:', error);
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
}
