import type { ReactNode } from "react";

interface OnboardingChoicesProps {
  // CTA for the "Upload files" card, supplied by the app layer. Keeping it a
  // slot is what lets this feature stay free of routing and of any dependency
  // on the uploads feature (see CLAUDE.md → Frontend Import Rules).
  uploadSlot: ReactNode;
}

// The post-signup "choose how to get started" screen. Purely presentational:
// the only interactive bit (the upload modal trigger) arrives as `uploadSlot`.
export default function OnboardingChoices({
  uploadSlot,
}: OnboardingChoicesProps) {
  return (
    <div className="onboarding">
      <header className="onboarding__header">
        <h1 className="onboarding__title">Welcome to Hexagone</h1>
        <p className="onboarding__subtitle">
          Choose how you&apos;d like to get started
        </p>
      </header>

      <ul className="onboarding__cards">
        <li className="onboarding__card onboarding__card--upload">
          <span className="onboarding__icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                d="M12 16V4m0 0L7 9m5-5 5 5"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <h2 className="onboarding__card-title">Upload files</h2>
          <p className="onboarding__card-desc">
            Import your hexes from a GPX file.
          </p>
          <div className="onboarding__card-action">{uploadSlot}</div>
        </li>

        <li className="onboarding__card onboarding__card--strava onboarding__card--soon">
          <span className="onboarding__badge">Coming soon</span>
          <span className="onboarding__icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                d="m8 3 5 9h-3l3 6 5-9h-3L8 3Z"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <h2 className="onboarding__card-title">Strava sync</h2>
          <p className="onboarding__card-desc">
            Pull activities straight from your Strava.
          </p>
          <div className="onboarding__card-action">
            <button type="button" className="button" disabled>
              Connect Strava
            </button>
          </div>
        </li>

        <li className="onboarding__card onboarding__card--demo onboarding__card--soon">
          <span className="onboarding__badge">Coming soon</span>
          <span className="onboarding__icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" strokeWidth="2" />
              <path
                d="m15.5 8.5-2 5-5 2 2-5 5-2Z"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <h2 className="onboarding__card-title">Explore a demo</h2>
          <p className="onboarding__card-desc">
            Look around with ready-made sample data.
          </p>
          <div className="onboarding__card-action">
            <button type="button" className="button" disabled>
              Explore demo
            </button>
          </div>
        </li>
      </ul>
    </div>
  );
}
