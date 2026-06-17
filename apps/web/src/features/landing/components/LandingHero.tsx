import type { ReactNode } from "react";

interface LandingHeroProps {
  // CTAs and visuals are slots supplied by the app layer. Keeping them as slots
  // is what lets this feature stay free of routing (the route owns the actual
  // <Link>s) and free of any dependency on how the animations are built — see
  // CLAUDE.md → Frontend Import Rules.
  navCta: ReactNode;
  heroCta: ReactNode;
  closingCta: ReactNode;
  traceVisual: ReactNode;
}

// The marketing landing page ("/"). A single-conversion-goal hero: one CTA,
// repeated, with the product's core magic (trace a route, ring a territory)
// shown as the supporting visuals. Purely presentational.
export default function LandingHero({
  navCta,
  heroCta,
  closingCta,
  traceVisual,
}: LandingHeroProps) {
  return (
    <div className="landing">
      <header className="landing__nav">
        <p className="landing__brand">
          <span className="landing__brand-mark" aria-hidden="true">
            ⬡
          </span>{" "}
          Hexa<span className="landing__brand-fade">gone</span>
        </p>
        {navCta}
      </header>

      <main className="landing__main">
        <section className="landing__hero landing__section">
          <div className="landing__hero-body">
            {/* TODO: Consider adding an eyebrow label */}
            {/* <p className="landing__eyebrow">Turn your runs into territory</p> */}
            <h1 className="landing__title">Run the map. Claim the world.</h1>
            <p className="landing__lead">
              Every kilometre you log colours in the map. Hexagone turns your
              GPX tracks into a living atlas of everywhere you&rsquo;ve been
              &mdash; and everywhere left to explore.
            </p>
            <div className="landing__cta-group">{heroCta}</div>
            <p className="landing__cta-note">Request early access</p>
          </div>
          <div className="landing__hero-media">
            <figure className="landing__figure">
              {traceVisual}
              <figcaption className="landing__caption">
                Your route, drawn live &mdash; hexes light up as you pass them.
              </figcaption>
            </figure>
          </div>
        </section>
      </main>

      <footer className="landing__footer">
        Hexagone &middot; Run the map. Claim the world &middot;{" "}
      </footer>
    </div>
  );
}
