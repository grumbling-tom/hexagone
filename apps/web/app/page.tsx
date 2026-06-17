import type { Metadata } from "next";
import Link from "next/link";
import LandingHero from "@/features/landing/components/LandingHero";
import TraceAnimation from "@/features/landing/components/TraceAnimation";
import TraceLoop from "@/features/landing/components/TraceLoop";

// Landing page (server component) — statically prerendered. The route owns
// navigation, handing the (routing-free) LandingHero its CTAs as <Link> slots.
// The authed app lives at /map and /uploads (App Router segments under
// (authed)).
export const metadata: Metadata = {
  title: "Hexagone — Run the map. Claim the world.",
  description:
    "Hexagone turns your GPX tracks into a living map of everywhere you've explored. Colour in the hexes you've covered and claim whole areas with a ring.",
};

export default function LandingPage() {
  return (
    <LandingHero
      navCta={
        <Link className="button button--secondary" href="/login">
          Login
        </Link>
      }
      heroCta={
        <Link className="button button--primary button--lg" href="/signup">
          Claim your first hex
        </Link>
      }
      closingCta={
        <Link className="button button--primary button--lg" href="/signup">
          Claim your first hex
        </Link>
      }
      traceVisual={
        <TraceLoop>
          <TraceAnimation />
        </TraceLoop>
      }
    />
  );
}
