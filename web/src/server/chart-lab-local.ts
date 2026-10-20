const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost"]);
const LOCAL_PORTS = new Set(["3010", "8780"]);

export function isChartLabLocalHost(hostHeader: string | null, forwardedHost: string | null = null): boolean {
  if (!hostHeader) return false;
  try {
    const url = new URL(`http://${hostHeader}`);
    return LOCAL_HOSTS.has(url.hostname.toLowerCase()) && (!url.port || LOCAL_PORTS.has(url.port)) &&
      (!forwardedHost || isChartLabLocalHost(forwardedHost));
  } catch {
    return false;
  }
}

export function isChartLabLocalRequest(request: Request, mutation = false): boolean {
  let url: URL;
  try { url = new URL(request.url); } catch { return false; }
  const hostHeader = request.headers.get("host")?.toLowerCase();
  const forwardedHost = request.headers.get("x-forwarded-host");
  if (url.protocol !== "http:" || !LOCAL_PORTS.has(url.port) || !LOCAL_HOSTS.has(url.hostname.toLowerCase())) return false;
  if (hostHeader && !isChartLabLocalHost(hostHeader)) return false;
  if (forwardedHost && !isChartLabLocalHost(forwardedHost)) return false;
  if (!mutation) return true;

  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    if (new URL(origin).origin !== url.origin) return false;
  } catch { return false; }
  const fetchSite = request.headers.get("sec-fetch-site");
  return fetchSite === null || fetchSite === "same-origin";
}
