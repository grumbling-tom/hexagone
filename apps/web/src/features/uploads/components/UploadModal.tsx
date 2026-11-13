"use client";

import { useRef, useState } from "react";
import {
  type CreateUploadRequest,
  type UploadResponse,
  UploadStatusValue,
} from "@/__generated__/backend-client/backend.schemas";

// "processing": bytes are in storage and the backend is turning them into
// hexagons. "invalid": processed, but the file couldn't be used (a terminal
// outcome, so it isn't retried). "error": something failed that a retry may fix.
type FileStatus =
  | "queued"
  | "uploading"
  | "processing"
  | "done"
  | "invalid"
  | "error";

interface FileItem {
  id: string;
  file: File;
  status: FileStatus;
  progress: number;
  error?: string;
  // Set once the bytes are in storage, so a retry only re-runs processing
  // instead of creating a second upload record.
  uploadUid?: string;
}

interface UploadModalProps {
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
  // Server action that processes a landed file and returns its final status.
  processUpload: (uploadUid: string) => Promise<UploadResponse>;
  onComplete: () => void | Promise<void>;
  onClose: () => void;
}

// PUT the file bytes straight to object storage, reporting progress. fetch()
// can't surface upload progress in browsers yet, so we drop to XHR for this leg.
function putWithProgress(
  url: string,
  headers: Record<string, string>,
  file: File,
  onProgress: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    for (const [key, value] of Object.entries(headers)) {
      xhr.setRequestHeader(key, value);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(file);
  });
}

// Per-file byte-progress ring geometry (r=9 in a 24×24 viewBox).
const RING_RADIUS = 9;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

const STEPS = ["Select", "Confirm", "Done"] as const;

export default function UploadModal({
  requestUpload,
  processUpload,
  onComplete,
  onClose,
}: UploadModalProps) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const updateFile = (id: string, patch: Partial<FileItem>) =>
    setFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const gpx = Array.from(incoming).filter((file) =>
      file.name.toLowerCase().endsWith(".gpx"),
    );
    setFiles((prev) => {
      const seen = new Set(
        prev.map((item) => `${item.file.name}:${item.file.size}`),
      );
      const additions = gpx
        .filter((file) => !seen.has(`${file.name}:${file.size}`))
        .map((file) => ({
          id: crypto.randomUUID(),
          file,
          status: "queued" as const,
          progress: 0,
        }));
      return [...prev, ...additions];
    });
  };

  const removeFile = (id: string) =>
    setFiles((prev) => prev.filter((item) => item.id !== id));

  // Create the upload record, PUT the bytes to the presigned URL, then ask the
  // backend to process them. Resolves true once the file has an outcome (on
  // the map, or rejected as invalid); on failure it records the error on the
  // item and resolves false (so a Promise.all of several uploads never
  // short-circuits).
  const uploadOne = async (item: FileItem): Promise<boolean> => {
    let uploadUid = item.uploadUid;
    try {
      if (!uploadUid) {
        updateFile(item.id, {
          status: "uploading",
          progress: 0,
          error: undefined,
        });
        const upload = await requestUpload({
          original_filename: item.file.name,
          file_size_bytes: item.file.size,
        });
        if (!upload.presigned_url) {
          throw new Error("No upload URL returned.");
        }
        await putWithProgress(
          upload.presigned_url,
          upload.required_headers ?? {},
          item.file,
          (percent) => updateFile(item.id, { progress: percent }),
        );
        uploadUid = upload.uid;
      }
      updateFile(item.id, {
        status: "processing",
        progress: 100,
        error: undefined,
        uploadUid,
      });

      let processed: UploadResponse;
      try {
        processed = await processUpload(uploadUid);
      } catch {
        throw new Error("Couldn't process the file. Try again.");
      }
      if (processed.current_status === UploadStatusValue.UPLOAD_INVALID) {
        updateFile(item.id, {
          status: "invalid",
          error: processed.current_status_detail ?? "Invalid GPX file",
        });
      } else {
        updateFile(item.id, { status: "done" });
      }
      return true;
    } catch (err) {
      updateFile(item.id, {
        status: "error",
        error: err instanceof Error ? err.message : "Upload failed.",
      });
      return false;
    }
  };

  const handleSubmit = async () => {
    // Upload everything not already done — covers a first run and retrying
    // files that failed on a previous attempt.
    const targets = files.filter(
      (item) => item.status === "queued" || item.status === "error",
    );
    if (targets.length === 0) return;

    setIsUploading(true);
    await Promise.all(targets.map(uploadOne));
    setIsUploading(false);
  };

  const hasUploadable = files.some(
    (item) => item.status === "queued" || item.status === "error",
  );
  const hasErrors = files.some((item) => item.status === "error");

  // The overall bar is by file COUNT, not bytes: each file is 1/N of the bar
  // and jumps it the same amount whether it succeeds or fails — failures just
  // land in a darker shade. (Smooth byte-level feedback lives in the per-file
  // rings instead.) The bar shows once at least one file has started.
  const total = files.length;
  const doneCount = files.filter((item) => item.status === "done").length;
  const invalidCount = files.filter((item) => item.status === "invalid").length;
  const errorCount =
    files.filter((item) => item.status === "error").length + invalidCount;
  const hasStarted = files.some((item) => item.status !== "queued");
  const donePercent = total === 0 ? 0 : Math.round((doneCount / total) * 100);
  const resolvedPercent =
    total === 0 ? 0 : Math.round(((doneCount + errorCount) / total) * 100);

  // Stepper position: pressing Upload/Retry puts a run in flight and advances to
  // Done (so Confirm goes solid); a failure drops back to Confirm; having files
  // selected sits on Confirm; nothing selected is Select.
  const isDone = total > 0 && doneCount + invalidCount === total;
  const currentStep = isUploading || isDone ? 2 : total > 0 ? 1 : 0;

  return (
    <div className="upload-modal">
      <button
        type="button"
        className="upload-modal__backdrop"
        aria-label="Close upload dialog"
        onClick={() => !isUploading && onClose()}
      />
      <div
        className="upload-modal__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <header className="upload-modal__header">
          <h2 className="upload-modal__title" id="upload-modal-title">
            Upload GPX files
          </h2>
          <button
            type="button"
            className="upload-modal__close"
            aria-label="Close"
            onClick={onClose}
            disabled={isUploading}
          >
            ×
          </button>
        </header>

        <ol className="upload-modal__steps">
          {STEPS.map((label, index) => (
            <li
              key={label}
              className={
                index === currentStep
                  ? "upload-modal__step upload-modal__step--active"
                  : index < currentStep
                    ? "upload-modal__step upload-modal__step--complete"
                    : "upload-modal__step"
              }
            >
              <span className="upload-modal__step-num">{index + 1}</span>
              <span className="upload-modal__step-label">{label}</span>
            </li>
          ))}
        </ol>

        {isDone ? (
          <div className="upload-modal__done">
            <p className="upload-modal__done-text">
              {invalidCount === 0
                ? total === 1
                  ? "Your run is on the map."
                  : `All ${total} runs are on your map.`
                : doneCount === 0
                  ? total === 1
                    ? "That file couldn't be read, so nothing was added."
                    : "None of these files could be read, so nothing was added."
                  : `${doneCount} of ${total} files added to your map. ${invalidCount} couldn't be read.`}
            </p>
            <button
              type="button"
              className="button button--primary"
              onClick={() => onComplete()}
            >
              View your map
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              className="upload-modal__dropzone"
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                addFiles(event.dataTransfer.files);
              }}
              disabled={isUploading}
            >
              <span className="upload-modal__dropzone-title">
                Drag GPX files here!
              </span>
              <span className="upload-modal__dropzone-hint">
                or click to browse
              </span>
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".gpx"
              multiple
              className="upload-modal__input"
              onChange={(event) => {
                addFiles(event.target.files);
                event.target.value = "";
              }}
            />

            {files.length > 0 && (
              <ul className="upload-modal__files">
                {files.map((item) => (
                  <li key={item.id} className="upload-modal__file">
                    <span className="upload-modal__file-name">
                      {item.file.name}
                    </span>
                    <span className="upload-modal__file-status">
                      {item.status === "uploading" && (
                        <svg
                          className="upload-modal__ring"
                          viewBox="0 0 24 24"
                          role="img"
                          aria-label={`Uploading, ${item.progress}%`}
                        >
                          <circle
                            className="upload-modal__ring-track"
                            cx="12"
                            cy="12"
                            r={RING_RADIUS}
                          />
                          <circle
                            className="upload-modal__ring-fill"
                            cx="12"
                            cy="12"
                            r={RING_RADIUS}
                            strokeDasharray={RING_CIRCUMFERENCE}
                            strokeDashoffset={
                              RING_CIRCUMFERENCE * (1 - item.progress / 100)
                            }
                          />
                        </svg>
                      )}
                      {item.status === "done" && (
                        <span
                          className="upload-modal__file-done"
                          role="img"
                          aria-label="Uploaded"
                        >
                          ✓
                        </span>
                      )}
                      {item.status === "processing" && (
                        <svg
                          className="upload-modal__ring"
                          viewBox="0 0 24 24"
                          role="img"
                          aria-label="Processing"
                        >
                          <circle
                            className="upload-modal__ring-fill"
                            cx="12"
                            cy="12"
                            r={RING_RADIUS}
                          />
                        </svg>
                      )}
                      {(item.status === "error" ||
                        item.status === "invalid") && (
                        <span className="upload-modal__file-error">
                          {item.error ?? "Failed"}
                        </span>
                      )}
                      {item.status === "queued" && (
                        <button
                          type="button"
                          className="upload-modal__file-remove"
                          aria-label={`Remove ${item.file.name}`}
                          onClick={() => removeFile(item.id)}
                        >
                          ×
                        </button>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {hasStarted && (
              <div className="upload-modal__overall">
                <div className="upload-modal__overall-track">
                  {/* Grey back-fill (done + failed counts) with the normal fill
                  (done count only) layered on top, so 0→done is the normal
                  colour, done→resolved is the grey failed shade, and the rest
                  is the track. */}
                  <progress
                    className="upload-modal__overall-bar upload-modal__overall-bar--failed"
                    value={resolvedPercent}
                    max={100}
                    aria-hidden="true"
                  />
                  <progress
                    className="upload-modal__overall-bar upload-modal__overall-bar--done"
                    value={donePercent}
                    max={100}
                    aria-label="Overall upload progress"
                  />
                </div>
                <span className="upload-modal__overall-pct">
                  {resolvedPercent}%
                </span>
              </div>
            )}

            <footer className="upload-modal__footer">
              <button
                type="button"
                className="button button--secondary"
                onClick={onClose}
                disabled={isUploading}
              >
                Cancel
              </button>
              <button
                type="button"
                className={
                  isUploading
                    ? "button button--primary button--pending"
                    : "button button--primary"
                }
                onClick={handleSubmit}
                disabled={!hasUploadable || isUploading}
              >
                {isUploading
                  ? "Uploading"
                  : hasErrors
                    ? "Retry failed"
                    : "Submit"}
              </button>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
