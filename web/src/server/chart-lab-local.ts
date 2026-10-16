const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost"]);

export function isChartLabLocalRequest(request: Request, mutation = false): boolean {
  let url: URL;
  try { url = new URL(request.url); } catch { return false; }
  const hostHeader = request.headers.get("host")?.toLowerCase();
  if (url.protocol !== "http:" || url.port !== "3010" || !LOCAL_HOSTS.has(url.hostname.toLowerCase())) return false;
  if (hostHeader) {
    try {
      const hostUrl = new URL(`http://${hostHeader}`);
      if (!LOCAL_HOSTS.has(hostUrl.hostname.toLowerCase()) || (hostUrl.port && hostUrl.port !== "3010")) return false;
    } catch { return false; }
  }
  if (!mutation) return true;

  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    if (new URL(origin).origin !== url.origin) return false;
  } catch { return false; }
  const fetchSite = request.headers.get("sec-fetch-site");
  return fetchSite === null || fetchSite === "same-origin";
}
