"use client";

import { useRef, useState } from "react";
import {
  type CreateUploadRequest,
  type UploadResponse,
  UploadStatusValue,
} from "@/__generated__/backend-client/backend.schemas";

type Status =
  | "idle"
  | "selected"
  | "creating"
  | "uploading"
  | "processing"
  | "success"
  | "error";

interface UploadFormProps {
  // Server action (supplied by the route) that creates the upload record and
  // returns a presigned URL. The file bytes are then PUT directly to object
  // storage from the browser — that leg does not touch the backend API.
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
  // Server action that processes a landed file and returns its final status.
  processUpload: (uploadUid: string) => Promise<UploadResponse>;
  onUploadComplete?: () => void;
  className?: string;
}

export default function UploadForm({
  requestUpload,
  processUpload,
  onUploadComplete,
  className = "",
}: UploadFormProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isBusy =
    status === "creating" || status === "uploading" || status === "processing";

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".gpx")) {
      setStatus("error");
      setErrorMessage("Please select a .gpx file.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setStatus("selected");
    setErrorMessage("");
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setStatus("idle");
    setErrorMessage("");
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleConfirm = async () => {
    if (!selectedFile) return;

    try {
      setStatus("creating");
      setErrorMessage("");

      const upload = await requestUpload({
        original_filename: selectedFile.name,
        file_size_bytes: selectedFile.size,
      });

      if (!upload.presigned_url) {
        throw new Error("No presigned URL returned.");
      }

      setStatus("uploading");

      const headers: Record<string, string> = upload.required_headers ?? {};
      const put = await fetch(upload.presigned_url, {
        method: "PUT",
        headers,
        body: selectedFile,
      });
      if (!put.ok) {
        throw new Error(`Upload failed (${put.status}). Please try again.`);
      }

      setStatus("processing");
      let processed: UploadResponse;
      try {
        processed = await processUpload(upload.uid);
      } catch {
        throw new Error("Couldn't process the file. Please try again.");
      }
      if (processed.current_status === UploadStatusValue.UPLOAD_INVALID) {
        throw new Error(
          `That file couldn't be used: ${processed.current_status_detail ?? "invalid GPX"}.`,
        );
      }

      setStatus("success");
      setSelectedFile(null);
      onUploadComplete?.();
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Upload failed. Please try again.",
      );
    } finally {
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  };

  const bemClass = "upload-form";
  const fullClass = className ? `${bemClass} ${className}` : bemClass;

  return (
    <div className={fullClass}>
      <input
        ref={inputRef}
        type="file"
        accept=".gpx"
        className="upload-form__input"
        id="gpx-upload"
        onChange={handleFileChange}
        disabled={isBusy}
      />
      {status === "selected" || isBusy ? (
        <div className="upload-form__confirm">
          <span className="upload-form__filename">{selectedFile?.name}</span>
          <button
            type="button"
            className="upload-form__confirm-button"
            onClick={handleConfirm}
            disabled={isBusy}
          >
            {status === "processing"
              ? "Processing…"
              : isBusy
                ? "Uploading…"
                : "Upload"}
          </button>
          <button
            type="button"
            className="upload-form__cancel-button"
            onClick={handleCancel}
            disabled={isBusy}
          >
            Cancel
          </button>
        </div>
      ) : (
        <label htmlFor="gpx-upload" className="upload-form__label">
          Choose GPX file
        </label>
      )}
      {status === "success" && (
        <span className="upload-form__message upload-form__message--success">
          File uploaded and added to your map.
        </span>
      )}
      {status === "error" && (
        <span className="upload-form__message upload-form__message--error">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
