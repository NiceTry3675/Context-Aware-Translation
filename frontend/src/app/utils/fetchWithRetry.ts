export interface RetryOptions {
  retries?: number;
  minDelayMs?: number; // initial backoff delay
  maxDelayMs?: number; // cap for backoff
  backoffFactor?: number; // exponential factor
  timeoutMs?: number; // per-attempt timeout
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
  opts: RetryOptions = {}
): Promise<Response> {
  const {
    retries = 3,
    minDelayMs = 500,
    maxDelayMs = 5000,
    backoffFactor = 2,
    timeoutMs = 10000,
  } = opts;

  let attempt = 0;
  let delay = minDelayMs;

  // Helper to run fetch with timeout via AbortController
  const doFetch = async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(input, { ...(init || {}), signal: controller.signal });
      return res;
    } finally {
      clearTimeout(timer);
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    try {
      const res = await doFetch();
      // Retry on 5xx and 429; otherwise return
      if (res.status >= 500 || res.status === 429) {
        if (attempt >= retries) return res; // give caller the error response
        // Respect Retry-After header if present
        const retryAfter = res.headers.get('retry-after');
        if (retryAfter) {
          const parsed = parseInt(retryAfter, 10);
          if (!Number.isNaN(parsed)) {
            await sleep(Math.min(parsed * 1000, maxDelayMs));
          } else {
            await sleep(Math.min(delay, maxDelayMs));
          }
        } else {
          await sleep(Math.min(delay, maxDelayMs));
        }
        attempt += 1;
        delay = Math.min(delay * backoffFactor, maxDelayMs);
        continue;
      }
      return res;
    } catch (err) {
      // Network error or timeout -> retry
      if (attempt >= retries) throw err;
      await sleep(Math.min(delay, maxDelayMs));
      attempt += 1;
      delay = Math.min(delay * backoffFactor, maxDelayMs);
    }
  }
}

