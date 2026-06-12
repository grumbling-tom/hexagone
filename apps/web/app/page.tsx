import Link from "next/link";

// Landing page (server component) — statically prerendered. The authed app lives
// at /map and /uploads (App Router segments under (authed)).
export default function LandingPage() {
  return (
    <main className="landing">
      <h1>Hexagone</h1>
      <p>Welcome to Hexagone.</p>
      <Link href="/map">Open App</Link>
    </main>
  );
}
