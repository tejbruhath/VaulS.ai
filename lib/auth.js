export function isAuthenticated(req) {
  // Check for Vercel auth header or session
  const token = req.headers.authorization?.split(' ')[1];
  const sessionToken = req.cookies?.sessionToken;

  return !!(token || sessionToken);
}

export function getUserId(req) {
  // Extract user ID from token or session
  const token = req.headers.authorization?.split(' ')[1];
  const userId = req.cookies?.userId;

  if (token) {
    try {
      // Decode JWT token (in production, verify signature)
      const payload = JSON.parse(Buffer.from(token.split('.')[1], 'base64'));
      return payload.sub || payload.user_id;
    } catch (e) {
      return null;
    }
  }

  return userId || 'anonymous';
}

export function requireAuth(handler) {
  return async (req, res) => {
    if (!isAuthenticated(req)) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
    return handler(req, res);
  };
}

export function setAuthCookie(res, token, userId) {
  res.setHeader('Set-Cookie', [
    `sessionToken=${token}; Path=/; HttpOnly; SameSite=Strict`,
    `userId=${userId}; Path=/; SameSite=Strict`,
  ]);
}

export function clearAuthCookie(res) {
  res.setHeader('Set-Cookie', [
    `sessionToken=; Path=/; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 UTC`,
    `userId=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 UTC`,
  ]);
}
