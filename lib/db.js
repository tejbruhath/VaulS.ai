import { sql } from '@vercel/postgres';

export async function initializeDatabase() {
  try {
    // Create tables if they don't exist
    await sql`
      CREATE TABLE IF NOT EXISTS repositories (
        id SERIAL PRIMARY KEY,
        owner VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        branch VARCHAR(255) DEFAULT 'main',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        indexed_at TIMESTAMP,
        status VARCHAR(50) DEFAULT 'pending',
        UNIQUE(owner, name, branch)
      );
    `;

    await sql`
      CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        repository_id INT NOT NULL REFERENCES repositories(id),
        file_path VARCHAR(1024) NOT NULL,
        content_hash VARCHAR(64),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(repository_id, file_path)
      );
    `;

    await sql`
      CREATE TABLE IF NOT EXISTS chunks (
        id SERIAL PRIMARY KEY,
        document_id INT NOT NULL REFERENCES documents(id),
        content TEXT NOT NULL,
        chunk_index INT NOT NULL,
        file_path VARCHAR(1024),
        start_line INT,
        end_line INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `;

    await sql`
      CREATE TABLE IF NOT EXISTS bm25_index (
        id SERIAL PRIMARY KEY,
        chunk_id INT UNIQUE REFERENCES chunks(id),
        text_vector tsvector,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `;

    await sql`
      CREATE INDEX IF NOT EXISTS idx_bm25_text ON bm25_index USING GIN (text_vector);
    `;

    await sql`
      CREATE TABLE IF NOT EXISTS query_logs (
        id SERIAL PRIMARY KEY,
        query TEXT NOT NULL,
        user_id VARCHAR(255),
        response_time INT,
        result_count INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `;

    console.log('Database initialized successfully');
    return true;
  } catch (error) {
    console.error('Database initialization error:', error);
    throw error;
  }
}

export async function queryDatabase(query, params = []) {
  try {
    return await sql(query, params);
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
}

export async function getRepositories() {
  const result = await sql`SELECT * FROM repositories ORDER BY created_at DESC`;
  return result.rows;
}

export async function addRepository(owner, name, branch = 'main') {
  const result = await sql`
    INSERT INTO repositories (owner, name, branch, status)
    VALUES (${owner}, ${name}, ${branch}, 'pending')
    ON CONFLICT (owner, name, branch) DO UPDATE SET status = 'pending'
    RETURNING *;
  `;
  return result.rows[0];
}

export async function addChunk(documentId, content, chunkIndex, filePath, startLine, endLine) {
  const result = await sql`
    INSERT INTO chunks (document_id, content, chunk_index, file_path, start_line, end_line)
    VALUES (${documentId}, ${content}, ${chunkIndex}, ${filePath}, ${startLine}, ${endLine})
    RETURNING *;
  `;
  return result.rows[0];
}

export async function searchChunks(query, limit = 10) {
  // Full-text search using PostgreSQL tsvector
  const result = await sql`
    SELECT c.*, d.file_path, r.owner, r.name
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    JOIN repositories r ON d.repository_id = r.id
    WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', ${query})
    LIMIT ${limit};
  `;
  return result.rows;
}

export async function getChunksByRepository(repositoryId, limit = 100) {
  const result = await sql`
    SELECT c.* FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.repository_id = ${repositoryId}
    LIMIT ${limit};
  `;
  return result.rows;
}
