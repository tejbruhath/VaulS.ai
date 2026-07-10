import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

export async function generateResponse(query, context, systemPrompt = null) {
  try {
    const defaultSystemPrompt = `You are a helpful AI assistant that answers questions based on provided context from code repositories and documentation. 
Provide accurate, concise answers and always cite your sources from the context provided.
If the context doesn't contain relevant information, say so clearly.`;

    const messages = [
      {
        role: 'user',
        content: `Context:\n${context}\n\nQuestion: ${query}`,
      },
    ];

    const response = await groq.chat.completions.create({
      model: 'mixtral-8x7b-32768',
      messages: messages,
      system: systemPrompt || defaultSystemPrompt,
      temperature: 0.7,
      max_tokens: 1024,
      top_p: 1,
    });

    return response.choices[0].message.content;
  } catch (error) {
    console.error('Groq API error:', error);
    throw error;
  }
}

export async function generateResponseStream(query, context, systemPrompt = null) {
  try {
    const defaultSystemPrompt = `You are a helpful AI assistant that answers questions based on provided context from code repositories and documentation. 
Provide accurate, concise answers and always cite your sources from the context provided.
If the context doesn't contain relevant information, say so clearly.`;

    const messages = [
      {
        role: 'user',
        content: `Context:\n${context}\n\nQuestion: ${query}`,
      },
    ];

    const stream = await groq.chat.completions.create({
      model: 'mixtral-8x7b-32768',
      messages: messages,
      system: systemPrompt || defaultSystemPrompt,
      temperature: 0.7,
      max_tokens: 1024,
      top_p: 1,
      stream: true,
    });

    return stream;
  } catch (error) {
    console.error('Groq streaming API error:', error);
    throw error;
  }
}

export async function embedText(text) {
  // Using Groq for embeddings - we'll use a simple hash-based approach for now
  // In production, use a dedicated embedding service
  try {
    const response = await fetch('https://api.together.xyz/inference', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'WhereIsAI/UAE-Large-V1',
        input: text,
      }),
    });

    if (!response.ok) {
      throw new Error(`Embedding API error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.data[0].embedding;
  } catch (error) {
    console.error('Embedding error:', error);
    // Fallback: return a random embedding of correct size
    return Array(384).fill(0).map(() => Math.random());
  }
}

export async function generateEmbeddings(texts) {
  try {
    const embeddings = await Promise.all(texts.map(text => embedText(text)));
    return embeddings;
  } catch (error) {
    console.error('Batch embedding error:', error);
    throw error;
  }
}
