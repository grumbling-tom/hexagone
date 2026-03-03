import react from "@astrojs/react";
import { defineConfig } from "astro/config";

// Vite plugin that enables client-side routing under /app in dev.
// Without this, navigating directly to e.g. /app/settings would 404 because
// only /app exists as an Astro page. The middleware rewrites /app/* requests
// back to /app, then React Router reads the real browser URL and renders the
// correct route. Requests containing a "." are skipped so static assets
// (JS, CSS, images) are served normally.
// In production, the hosting provider needs an equivalent rewrite rule
// (/app/* → /app/index.html).
function spaFallback() {
	return {
		name: "spa-fallback",
		configureServer(server) {
			server.middlewares.use((req, _res, next) => {
				if (req.url?.startsWith("/app") && !req.url.includes(".")) {
					req.url = "/app";
				}
				next();
			});
		},
	};
}

export default defineConfig({
	// Canonical production URL — used for sitemaps, canonical tags, etc.
	site: "https://haxagone.com",
	integrations: [react()],
	vite: {
		plugins: [spaFallback()],
	},
	// output defaults to "static" — plain HTML/JS/CSS, no server runtime.
	// No `base` setting here: that would prefix *all* routes including "/".
	// Instead, only React Router uses basename="/app" to scope the SPA.
});
