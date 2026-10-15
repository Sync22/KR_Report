const CACHE_TTL_MS = 30_000;
const MAX_CACHE_ENTRIES = 256;

type CacheEntry = { expiresAt: number; body: string };

const cache = new Map<string, CacheEntry>();

function jsonResponse(body: string, request: Request, cacheState: "hit" | "miss"): Response {
  const headers = {
    "content-type": "application/json",
    "cache-control": "no-store",
  };
  if (request.headers.get("x-stock-monitor-benchmark") === "1") {
    Object.assign(headers, { "x-stock-monitor-cache": cacheState });
  }
  return new Response(body, {
    headers,
  });
}

export function cachedStoredJsonResponse(
  request: Request,
  semanticInputs: readonly (string | number | boolean | null)[],
  build: () => unknown,
): Response {
  const url = new URL(request.url);
  const key = `${url.pathname}:${JSON.stringify(semanticInputs)}`;
  const now = performance.now();
  const cached = cache.get(key);
  if (cached && cached.expiresAt > now) return jsonResponse(cached.body, request, "hit");
  if (cached) cache.delete(key);

  const body = JSON.stringify(build());
  if (body === undefined) throw new TypeError("Stored response builder must return a JSON value");

  const savedAt = performance.now();
  for (const [entryKey, entry] of cache) {
    if (entry.expiresAt <= savedAt) cache.delete(entryKey);
  }
  while (cache.size >= MAX_CACHE_ENTRIES) cache.delete(cache.keys().next().value!);
  cache.set(key, { body, expiresAt: savedAt + CACHE_TTL_MS });
  return jsonResponse(body, request, "miss");
}
