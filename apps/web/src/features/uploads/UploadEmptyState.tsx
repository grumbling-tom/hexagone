"use client";

import UploadForm from "@/features/uploads/UploadForm";
import UploadHelp from "@/features/uploads/UploadHelp";

interface UploadEmptyStateProps {
  onUploadComplete?: () => void;
}

export default function UploadEmptyState({
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
      <UploadForm onUploadComplete={onUploadComplete} />
    </div>
  );
}
