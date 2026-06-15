"use client";

import { useRef, useState } from "react";
import type {
  CreateUploadRequest,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";

type FileStatus = "queued" | "uploading" | "done" | "error";

interface FileItem {
  id: string;
  file: File;
  status: FileStatus;
  progress: number;
  error?: string;
}

interface UploadModalProps {
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
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

  // Create the upload record, then PUT the bytes to the presigned URL. Resolves
  // true on success; on failure it records the error on the item and resolves
  // false (so a Promise.all of several uploads never short-circuits).
  const uploadOne = async (item: FileItem): Promise<boolean> => {
    updateFile(item.id, { status: "uploading", progress: 0, error: undefined });
    try {
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
      updateFile(item.id, { status: "done", progress: 100 });
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
  const errorCount = files.filter((item) => item.status === "error").length;
  const hasStarted = files.some(
    (item) =>
      item.status === "uploading" ||
      item.status === "done" ||
      item.status === "error",
  );
  const donePercent = total === 0 ? 0 : Math.round((doneCount / total) * 100);
  const resolvedPercent =
    total === 0 ? 0 : Math.round(((doneCount + errorCount) / total) * 100);

  // Stepper position: completing every upload marks all three steps done (Done
  // goes solid blue); a run in flight sits on Done; a failure drops back to
  // Confirm; having files selected sits on Confirm; nothing selected is Select.
  const isDone = total > 0 && doneCount === total;
  const currentStep = isDone ? 3 : isUploading ? 2 : total > 0 ? 1 : 0;

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

        {/* Keep the file list and progress visible once everything's done —
        swapping the whole body out for a bare confirmation is jarring. We only
        hide the dropzone (no more files to add) and replace the footer's
        actions with the completion message + CTA. */}
        {!isDone && (
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
          </>
        )}

        {files.length > 0 && (
          <ul className="upload-modal__files">
            {files.map((item) => (
              <li key={item.id} className="upload-modal__file">
                <span className="upload-modal__file-name">{item.file.name}</span>
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
                  {item.status === "error" && (
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
            <span className="upload-modal__overall-pct">{resolvedPercent}%</span>
          </div>
        )}

        {isDone ? (
          <div className="upload-modal__done">
            <p className="upload-modal__done-text">
              {total === 1
                ? "Your file is uploaded and now processing."
                : `All ${total} files are uploaded and now processing.`}
            </p>
            <button
              type="button"
              className="button button--primary upload-modal__done-action"
              onClick={() => onComplete()}
            >
              View your map
            </button>
          </div>
        ) : (
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
              {isUploading ? "Uploading" : hasErrors ? "Retry failed" : "Submit"}
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}
