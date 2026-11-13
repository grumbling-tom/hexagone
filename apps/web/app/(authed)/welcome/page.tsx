import { redirect } from "next/navigation";
import { UploadStatusValue } from "@/__generated__/backend-client/backend.schemas";
import { listUploads } from "@/__generated__/backend-client/uploads";
import OnboardingChoices from "@/features/onboarding/components/OnboardingChoices";
import { finishOnboarding } from "@/features/onboarding/server/finishOnboarding";
import UploadModalButton from "@/features/uploads/components/UploadModalButton";
import {
  processUpload,
  requestUpload,
} from "@/features/uploads/server/uploads";

export default async function WelcomePage() {
  // "New user" = no uploads that have reached the backend (RECEIVED / SUCCESS /
  // INVALID). UPLOAD_PENDING deliberately does NOT count: a failed browser→S3
  // PUT leaves a stuck PENDING record, and counting it would lock the user out
  // of onboarding with no way back to retry. Statuses are derived from the enum
  // (minus PENDING) rather than re-listed.
  const countedStatuses = Object.values(UploadStatusValue).filter(
    (status) => status !== UploadStatusValue.UPLOAD_PENDING,
  );
  const uploads = await listUploads({
    statuses: countedStatuses,
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
            processUpload={processUpload}
            onComplete={finishOnboarding}
          />
        }
      />
    </main>
  );
}
