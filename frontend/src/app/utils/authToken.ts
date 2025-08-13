// Simple client-side cache for Clerk JWTs to reduce redundant getToken() calls
// Works in client components only

let cachedToken: string | null = null;
let cachedTokenExpiryMs: number | null = null;

function decodeJwtExpiryMs(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const payloadJson = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson);
    if (typeof payload.exp === 'number') {
      return payload.exp * 1000; // seconds -> ms
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Returns a cached Clerk JWT if still valid; otherwise fetches a new one via provided getToken()
 * and caches it until near expiry.
 * minValidityMs: if the token will expire sooner than this, a fresh token will be fetched.
 */
export async function getCachedClerkToken(
  getTokenFn: () => Promise<string | null>,
  minValidityMs: number = 60_000
): Promise<string | null> {
  const now = Date.now();
  if (cachedToken && cachedTokenExpiryMs && cachedTokenExpiryMs - now > minValidityMs) {
    return cachedToken;
  }

  const fresh = await getTokenFn();
  if (!fresh) {
    cachedToken = null;
    cachedTokenExpiryMs = null;
    return null;
  }

  cachedToken = fresh;
  // If decode fails, fall back to a short cache window to avoid frequent refetches but limit risk
  cachedTokenExpiryMs = decodeJwtExpiryMs(fresh) || now + 60_000;
  return cachedToken;
}

export function clearCachedClerkToken(): void {
  cachedToken = null;
  cachedTokenExpiryMs = null;
}

/**
 * Returns the cached token only if present and sufficiently valid; never triggers a new fetch.
 * Useful for low-priority calls where we want to avoid issuing a new JWT.
 */
export function getCachedClerkTokenIfPresent(minValidityMs: number = 60_000): string | null {
  const now = Date.now();
  if (cachedToken && cachedTokenExpiryMs && cachedTokenExpiryMs - now > minValidityMs) {
    return cachedToken;
  }
  return null;
}

export async function buildAuthHeader(
  getTokenFn: () => Promise<string | null>
): Promise<Record<string, string>> {
  const token = await getCachedClerkToken(getTokenFn);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function buildOptionalAuthHeader(): Record<string, string> {
  const token = getCachedClerkTokenIfPresent();
  return token ? { Authorization: `Bearer ${token}` } : {};
}


