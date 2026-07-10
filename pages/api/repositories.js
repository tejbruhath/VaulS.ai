import { getRepositories, addRepository } from '../../lib/db';
import { requireAuth } from '../../lib/auth';

export default requireAuth(async function handler(req, res) {
  if (req.method === 'GET') {
    try {
      const repos = await getRepositories();
      return res.status(200).json({ repositories: repos });
    } catch (error) {
      console.error('Get repositories error:', error);
      return res.status(500).json({ error: 'Failed to fetch repositories' });
    }
  }

  if (req.method === 'POST') {
    const { owner, name, branch = 'main' } = req.body;

    if (!owner || !name) {
      return res.status(400).json({ error: 'Owner and name are required' });
    }

    try {
      const repo = await addRepository(owner, name, branch);
      
      // Queue indexing task
      // In production, this would trigger a background job
      console.log(`Repository ${owner}/${name} queued for indexing`);

      return res.status(201).json({
        message: 'Repository added',
        repository: repo,
      });
    } catch (error) {
      console.error('Add repository error:', error);
      return res.status(500).json({ error: 'Failed to add repository' });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
});
