import { redirect } from "next/navigation";
import { UploadStatusValue } from "@/__generated__/backend-client/backend.schemas";
import { listUploads } from "@/__generated__/backend-client/uploads";
import OnboardingChoices from "@/features/onboarding/components/OnboardingChoices";
import { finishOnboarding } from "@/features/onboarding/server/finishOnboarding";
import UploadModalButton from "@/features/uploads/components/UploadModalButton";
import { requestUpload } from "@/features/uploads/server/uploads";

export default async function WelcomePage() {
  // "New user" = zero uploads in ANY state. The list endpoint excludes
  // UPLOAD_PENDING by default, so every status is passed explicitly (derived
  // from the enum, not re-listed) — otherwise a user who has only just uploaded
  // (still pending) would read as new and bounce straight back here. The moment
  // a user has any upload, this page hands off to the map.
  const uploads = await listUploads({
    statuses: Object.values(UploadStatusValue),
    page_size: 1,
  });
  if (uploads.items.length > 0) {
    redirect("/map");
  }

  // The route is the one place allowed to wire two features together and own
  // navigation: it hands the upload feature a presigned-URL action and a
  // post-upload navigation action, and slots that button into the (routing-free,
  // uploads-agnostic) onboarding chooser.
  return (
    <main className="page onboarding-page">
      <OnboardingChoices
        uploadSlot={
          <UploadModalButton
            requestUpload={requestUpload}
            onComplete={finishOnboarding}
          />
        }
      />
    </main>
  );
}
