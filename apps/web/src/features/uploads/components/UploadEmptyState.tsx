"use client";

import type {
  CreateUploadRequest,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";
import UploadForm from "@/features/uploads/components/UploadForm";
import UploadHelp from "@/features/uploads/components/UploadHelp";

interface UploadEmptyStateProps {
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
  // Server action that processes a landed file and returns its final status.
  processUpload: (uploadUid: string) => Promise<UploadResponse>;
  onUploadComplete?: () => void;
}

export default function UploadEmptyState({
  requestUpload,
  processUpload,
  onUploadComplete,
}: UploadEmptyStateProps) {
  return (
    <div className="upload-empty-state">
      <h2 className="upload-empty-state__heading">Upload a GPX file</h2>
      <p className="upload-empty-state__text">
        Hexagone needs a GPX file to compute your areas of control - get started
        by uploading one!
      </p>
      <UploadHelp className="upload-empty-state__help" />
      <UploadForm
        requestUpload={requestUpload}
        processUpload={processUpload}
        onUploadComplete={onUploadComplete}
      />
    </div>
  );
}
