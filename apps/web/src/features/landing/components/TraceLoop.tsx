"use client";

import type { ReactNode } from "react";
import { TRACE_CYCLE_SECONDS } from "@/features/landing/geometry";

// Loops the (server-rendered) trace animation: play, hold on the finished map,
// then replay — forever. The animation itself is pure CSS; this client
// component only re-triggers it, by toggling the `hex-anim--playing` class and
// forcing a reflow. That's the one thing CSS can't do on its own:
// animation-delay only staggers the FIRST iteration, so an `infinite` CSS
// animation would re-pop every hex in sync after the first cascade.
//
// Without JS (or with reduced motion) the SVG simply shows its base state — the
// finished, fully-claimed map — so this is purely a progressive enhancement.
const CYCLE_MS = TRACE_CYCLE_SECONDS * 1000;

export default function TraceLoop({ children }: { children: ReactNode }) {
  // Ref callback with cleanup (React 19) rather than useEffect.
  const runLoop = (node: HTMLDivElement | null) => {
    if (!node) return;
    // Respect reduced motion: leave the finished state shown, never animate.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const play = () => {
      node.classList.remove("hex-anim--playing");
      void node.offsetWidth; // reflow so the cascade restarts cleanly
      node.classList.add("hex-anim--playing");
    };
    play();
    const id = window.setInterval(play, CYCLE_MS);
    return () => window.clearInterval(id);
  };

  return (
    <div className="hex-anim" ref={runLoop}>
      {children}
    </div>
  );
}
