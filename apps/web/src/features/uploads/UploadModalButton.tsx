"use client";

import { useState } from "react";
import type {
  CreateUploadRequest,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";
import UploadModal from "./UploadModal";

interface UploadModalButtonProps {
  // Server action that creates the upload record and returns a presigned URL.
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
  // Where to go once the user has uploaded at least one file. Supplied by the
  // app layer (a server action that redirects) so this feature never imports
  // routing — it just calls the function it is handed.
  onComplete: () => void | Promise<void>;
}

export default function UploadModalButton({
  requestUpload,
  onComplete,
}: UploadModalButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="button button--primary"
        onClick={() => setOpen(true)}
      >
        Upload file
      </button>
      {open && (
        <UploadModal
          requestUpload={requestUpload}
          onComplete={onComplete}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
