// Landing page (server component) — replaces src/pages/index.astro. The app
// itself lives at /app, mounted client-side (app/app/[[...slug]]/page.tsx).
export default function LandingPage() {
  return (
    <main className="landing">
      <h1>Hexagone</h1>
      <p>Welcome to Hexagone.</p>
      <a href="/app">Open App</a>
    </main>
  );
}
