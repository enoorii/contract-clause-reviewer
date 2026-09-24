/**
 * Token Utilities
 * JWT parsing and inspection helpers.
 * Also used for proactive refresh
 */

interface JwtPayload {
  sub: string;
  exp: number;
  type: string;
  jti: string;
}

/**
 * Decodes a JWT payload without verification.
 * WARNING: This is for inspection only. Never trust client-side JWT validation for security.
 */
export function decodeJwt(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1]));
    return payload as JwtPayload;
  } catch {
    return null;
  }
}

/**
 * Checks if a JWT is expired based on its 'exp' claim.
 * Returns true if expired or invalid.
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJwt(token);
  if (!payload || !payload.exp) return true;

  // Add 30-second buffer to account for clock skew
  const now = Math.floor(Date.now() / 1000);
  return payload.exp <= now + 30;
}

/**
 * Gets the expiration time of a JWT in milliseconds since epoch.
 */
export function getTokenExpiration(token: string): number | null {
  const payload = decodeJwt(token);
  if (!payload || !payload.exp) return null;
  return payload.exp * 1000;
}
