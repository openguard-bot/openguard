export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/dashboard/")) {
      const strippedPath = url.pathname.replace("/dashboard", "") || "/";

      // Try to serve static asset first
      const assetRequest = new Request(
        new URL(strippedPath, request.url),
        request
      );
      const assetResponse = await env.ASSETS.fetch(assetRequest);

      // If asset exists, serve it
      if (assetResponse.status !== 404) {
        return assetResponse;
      }

      // Fallback: serve index.html for client-side routes
      const indexRequest = new Request(
        new URL("/index.html", request.url),
        request
      );
      return env.ASSETS.fetch(indexRequest);
    }

    // Not under /dashboard/, return 404
    return new Response("Not Found", { status: 404 });
  },
};
