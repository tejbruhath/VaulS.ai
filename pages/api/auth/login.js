import { setAuthCookie } from '../../../lib/auth';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' });
  }

  try {
    // In production, verify against a database
    // For demo, accept any non-empty credentials
    const token = Buffer.from(JSON.stringify({ 
      sub: email, 
      iat: Date.now() 
    })).toString('base64');

    setAuthCookie(res, token, email);

    return res.status(200).json({
      success: true,
      user: { email },
      message: 'Logged in successfully',
    });
  } catch (error) {
    console.error('Login error:', error);
    return res.status(500).json({ error: 'Login failed' });
  }
}
