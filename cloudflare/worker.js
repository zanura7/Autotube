export default {
  async fetch(request, env) {
    const incomingUrl = new URL(request.url);

    if (incomingUrl.pathname === "/be" || incomingUrl.pathname.startsWith("/be/")) {
      const upstreamUrl = new URL(request.url);
      upstreamUrl.protocol = "http:";
      upstreamUrl.hostname = "autotube.internal";
      upstreamUrl.port = "8000";
      upstreamUrl.pathname = incomingUrl.pathname.slice(3) || "/";

      try {
        return await env.AUTOTUBE_API.fetch(new Request(upstreamUrl, request));
      } catch {
        return Response.json(
          { status: "unavailable", detail: "Autotube backend is unavailable" },
          { status: 503, headers: { "cache-control": "no-store" } },
        );
      }
    }

    return env.ASSETS.fetch(request);
  },
};
