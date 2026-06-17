import type { Metadata } from "next";
import Link from "next/link";
import LandingHero from "@/features/landing/components/LandingHero";

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
        <Link className="button button--primary" href="/signup">
          Start claiming
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
      // Slice 1 placeholder — replaced by the trace animation in slice 2.
      traceVisual={
        <img
          className="landing__media"
          src="/map.png"
          alt="A city map with a running route and claimed hexagons"
        />
      }
    />
  );
}
