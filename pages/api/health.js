import { sql } from '@vercel/postgres';
import { getQdrantStats } from '../../lib/qdrant';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {},
  };

  // Check PostgreSQL
  try {
    await sql`SELECT 1`;
    health.services.postgres = 'connected';
  } catch (error) {
    health.services.postgres = `error: ${error.message}`;
    health.status = 'degraded';
  }

  // Check Qdrant
  try {
    const stats = await getQdrantStats();
    health.services.qdrant = stats ? 'connected' : 'error';
  } catch (error) {
    health.services.qdrant = `error: ${error.message}`;
    health.status = 'degraded';
  }

  // Check Groq API
  try {
    const groqKey = !!process.env.GROQ_API_KEY;
    health.services.groq = groqKey ? 'configured' : 'not configured';
  } catch (error) {
    health.services.groq = 'error';
    health.status = 'degraded';
  }

  const statusCode = health.status === 'ok' ? 200 : 503;
  return res.status(statusCode).json(health);
}
