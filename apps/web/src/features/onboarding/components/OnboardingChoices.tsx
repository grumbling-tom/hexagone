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
        <OnboardingCard
          variant="upload"
          icon={
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
          }
          title="Upload files"
          description="Import your hexes from a GPX file."
          action={uploadSlot}
        />

        <OnboardingCard
          variant="strava"
          comingSoon
          icon={
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
          }
          title="Strava sync"
          description="Pull activities straight from your Strava."
          action={
            <button type="button" className="button" disabled>
              Connect Strava
            </button>
          }
        />

        <OnboardingCard
          variant="demo"
          comingSoon
          icon={
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
          }
          title="Explore a demo"
          description="Look around with ready-made sample data."
          action={
            <button type="button" className="button" disabled>
              Explore demo
            </button>
          }
        />
      </ul>
    </div>
  );
}

interface OnboardingCardProps {
  // Drives the accent colour (onboarding__card--<variant>) via CSS.
  variant: "upload" | "strava" | "demo";
  icon: ReactNode;
  title: string;
  description: string;
  // The CTA — a slot so the upload card can take an interactive trigger while
  // the coming-soon cards pass a disabled button.
  action: ReactNode;
  // Shows the "Coming soon" badge and dims the card.
  comingSoon?: boolean;
}

function OnboardingCard({
  variant,
  icon,
  title,
  description,
  action,
  comingSoon = false,
}: OnboardingCardProps) {
  const className = [
    "onboarding__card",
    `onboarding__card--${variant}`,
    comingSoon && "onboarding__card--soon",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <li className={className}>
      {comingSoon && <span className="onboarding__badge">Coming soon</span>}
      <span className="onboarding__icon" aria-hidden="true">
        {icon}
      </span>
      <h2 className="onboarding__card-title">{title}</h2>
      <p className="onboarding__card-desc">{description}</p>
      <div className="onboarding__card-action">{action}</div>
    </li>
  );
}
