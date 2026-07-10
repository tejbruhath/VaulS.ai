const QDRANT_URL = process.env.QDRANT_URL || 'http://localhost:6333';
const QDRANT_API_KEY = process.env.QDRANT_API_KEY;

const COLLECTION_NAME = 'rag_embeddings';
const VECTOR_SIZE = 384;

export async function initializeQdrant() {
  try {
    const response = await fetch(`${QDRANT_URL}/collections`, {
      headers: {
        'api-key': QDRANT_API_KEY,
      },
    });
    
    const data = await response.json();
    const exists = data.result.some(c => c.name === COLLECTION_NAME);

    if (!exists) {
      await fetch(`${QDRANT_URL}/collections/${COLLECTION_NAME}`, {
        method: 'PUT',
        headers: {
          'api-key': QDRANT_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vectors: {
            size: VECTOR_SIZE,
            distance: 'Cosine',
          },
        }),
      });
      console.log(`Qdrant collection '${COLLECTION_NAME}' created`);
    }
    return true;
  } catch (error) {
    console.error('Qdrant initialization error:', error);
    throw error;
  }
}

export async function upsertVector(pointId, vector, payload) {
  try {
    await fetch(`${QDRANT_URL}/collections/${COLLECTION_NAME}/points?wait=true`, {
      method: 'PUT',
      headers: {
        'api-key': QDRANT_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        points: [
          {
            id: pointId,
            vector: vector,
            payload: payload,
          },
        ],
      }),
    });
  } catch (error) {
    console.error('Qdrant upsert error:', error);
    throw error;
  }
}

export async function searchVectors(query, limit = 10, scoreThreshold = 0.6) {
  try {
    const response = await fetch(`${QDRANT_URL}/collections/${COLLECTION_NAME}/points/search`, {
      method: 'POST',
      headers: {
        'api-key': QDRANT_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vector: query,
        limit: limit,
        score_threshold: scoreThreshold,
      }),
    });
    
    const data = await response.json();
    return data.result || [];
  } catch (error) {
    console.error('Qdrant search error:', error);
    throw error;
  }
}

export async function deleteVector(pointId) {
  try {
    await fetch(`${QDRANT_URL}/collections/${COLLECTION_NAME}/points?wait=true`, {
      method: 'DELETE',
      headers: {
        'api-key': QDRANT_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        points_selector: {
          ids: [pointId],
        },
      }),
    });
  } catch (error) {
    console.error('Qdrant delete error:', error);
    throw error;
  }
}

export async function getQdrantStats() {
  try {
    const response = await fetch(`${QDRANT_URL}/collections/${COLLECTION_NAME}`, {
      headers: {
        'api-key': QDRANT_API_KEY,
      },
    });
    
    const data = await response.json();
    return {
      points_count: data.result.points_count,
      vectors_count: data.result.vectors_count,
      status: data.result.status,
    };
  } catch (error) {
    console.error('Qdrant stats error:', error);
    return null;
  }
}
