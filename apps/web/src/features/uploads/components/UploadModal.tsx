"use client";

import { useRef, useState } from "react";
import type {
  CreateUploadRequest,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";

interface SelectedFile {
  id: string;
  file: File;
}

interface UploadModalProps {
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
  onComplete: () => void | Promise<void>;
  onClose: () => void;
}

export default function UploadModal({ onClose }: UploadModalProps) {
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

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
        .map((file) => ({ id: crypto.randomUUID(), file }));
      return [...prev, ...additions];
    });
  };

  const removeFile = (id: string) =>
    setFiles((prev) => prev.filter((item) => item.id !== id));

  return (
    <div className="upload-modal">
      <button
        type="button"
        className="upload-modal__backdrop"
        aria-label="Close upload dialog"
        onClick={onClose}
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
          >
            ×
          </button>
        </header>

        <button
          type="button"
          className="upload-modal__dropzone"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            addFiles(event.dataTransfer.files);
          }}
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
            {files.map(({ id, file }) => (
              <li key={id} className="upload-modal__file">
                <span className="upload-modal__file-name">{file.name}</span>
                <button
                  type="button"
                  className="upload-modal__file-remove"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => removeFile(id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        <footer className="upload-modal__footer">
          <button
            type="button"
            className="button button--secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="button button--primary"
            disabled={files.length === 0}
          >
            Submit
          </button>
        </footer>
      </div>
    </div>
  );
}
