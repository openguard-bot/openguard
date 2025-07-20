export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;

    // Redirect /dashboard to /dashboard/ for canonical path
    if (pathname === '/dashboard') {
      return Response.redirect(`${url.origin}/dashboard/`, 301);
    }

    // Only handle requests under the /dashboard/ path
    if (pathname.startsWith('/dashboard/')) {
      // Create a new URL object with the path rewritten for asset lookup
      // e.g., /dashboard/login -> /login
      const assetUrl = new URL(url);
      assetUrl.pathname = pathname.substring('/dashboard'.length);

      // Create a new request with the rewritten URL
      const assetRequest = new Request(assetUrl, request);

      // Fetch from assets, but DO NOT automatically follow redirects.
      const response = await env.ASSETS.fetch(assetRequest, { redirect: 'manual' });

      // If wrangler's dev server sends a redirect OR the asset isn't found,
      // serve the SPA's index.html as the fallback.
      if (response.status === 307 || response.status === 301 || response.status === 302 || response.status === 404) {
        // Fetch the entrypoint from the root of your assets
        const spaUrl = new URL('/index.html', url.origin);
        return env.ASSETS.fetch(new Request(spaUrl));
      }

      // Otherwise, return the asset
      return response;
    }

    // For any other path, return 404
    return new Response('Not Found', { status: 404 });
  },
};