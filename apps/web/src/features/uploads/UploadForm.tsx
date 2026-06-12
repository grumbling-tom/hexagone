"use client";

import { useRef, useState } from "react";
import { useCreateUpload } from "@/__generated__/backend-client/uploads";

type Status =
  | "idle"
  | "selected"
  | "creating"
  | "uploading"
  | "success"
  | "error";

interface UploadFormProps {
  onUploadComplete?: () => void;
  className?: string;
}

export default function UploadForm({
  onUploadComplete,
  className = "",
}: UploadFormProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutateAsync: createUpload } = useCreateUpload();

  const isBusy = status === "creating" || status === "uploading";

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

      const upload = await createUpload({
        data: {
          original_filename: selectedFile.name,
          file_size_bytes: selectedFile.size,
        },
      });

      if (!upload.presigned_url) {
        throw new Error("No presigned URL returned.");
      }

      setStatus("uploading");

      const headers: Record<string, string> = upload.required_headers ?? {};
      await fetch(upload.presigned_url, {
        method: "PUT",
        headers,
        body: selectedFile,
      });

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
            {isBusy ? "Uploading…" : "Upload"}
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
          File uploaded successfully. It will be processed shortly.
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
