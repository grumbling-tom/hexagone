import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type {
  PaginatedResultUploadResponse,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";
import { UploadStatusValue } from "@/__generated__/backend-client/backend.schemas";
import {
  getListUploadsQueryKey,
  useListUploads,
} from "@/__generated__/backend-client/uploads";
import UploadForm from "@/components/UploadForm";
import UploadHelp from "@/components/UploadHelp";

const STATUS_LABELS: Record<string, { label: string; modifier: string }> = {
  [UploadStatusValue.UPLOAD_PENDING]: {
    label: "Pending",
    modifier: "pending",
  },
  [UploadStatusValue.UPLOAD_RECEIVED]: {
    label: "Processing",
    modifier: "processing",
  },
  [UploadStatusValue.UPLOAD_SUCCESS]: {
    label: "Processed",
    modifier: "success",
  },
  [UploadStatusValue.UPLOAD_INVALID]: {
    label: "Invalid",
    modifier: "invalid",
  },
};

function StatusBadge({ status }: { status: string }) {
  const info = STATUS_LABELS[status] ?? { label: status, modifier: "" };
  const className = info.modifier
    ? `upload-status-badge upload-status-badge--${info.modifier}`
    : "upload-status-badge";
  return <span className={className}>{info.label}</span>;
}

function ordinal(day: number): string {
  if (day >= 11 && day <= 13) return `${day}th`;
  switch (day % 10) {
    case 1:
      return `${day}st`;
    case 2:
      return `${day}nd`;
    case 3:
      return `${day}rd`;
    default:
      return `${day}th`;
  }
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  const day = ordinal(date.getDate());
  const month = date.toLocaleDateString("en-GB", { month: "long" });
  const year = date.getFullYear();
  return `${day} ${month} ${year}`;
}

export default function UploadList() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const snapshotRef = useRef<string | null>(null);
  const refreshingRef = useRef(false);

  const { data, isLoading, isError, isFetching } = useListUploads({
    page_size: 10,
    cursor: cursor ?? undefined,
  });

  const dataFingerprint = useCallback(
    (d: PaginatedResultUploadResponse) =>
      d.items.map((i) => `${i.uid}:${i.current_status}`).join(","),
    [],
  );

  useEffect(() => {
    if (refreshingRef.current && !isFetching && data) {
      refreshingRef.current = false;
      const current = dataFingerprint(data);
      if (current === snapshotRef.current) {
        setRefreshMessage("Already up to date.");
      } else {
        setRefreshMessage(null);
      }
      snapshotRef.current = null;
    }
  }, [isFetching, data, dataFingerprint]);

  const handleRefresh = () => {
    setRefreshMessage(null);
    if (data) {
      snapshotRef.current = dataFingerprint(data);
    }
    refreshingRef.current = true;
    queryClient.invalidateQueries({ queryKey: getListUploadsQueryKey() });
  };

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: getListUploadsQueryKey() });
  };

  const handleNext = () => {
    if (data?.next_cursor) {
      setCursorHistory((prev) => [...prev, cursor ?? ""]);
      setCursor(data.next_cursor);
    }
  };

  const handlePrevious = () => {
    setCursorHistory((prev) => {
      const next = [...prev];
      const previous = next.pop();
      setCursor(previous || null);
      return next;
    });
  };

  const isFirstPage = cursorHistory.length === 0 && !cursor;
  const isEmpty = isFirstPage && !isLoading && data?.items.length === 0;

  return (
    <>
      <section className="upload-section">
        <h2>Upload a GPX file</h2>
        <UploadForm onUploadComplete={handleUploadComplete} />
        <UploadHelp className="upload-section__help" />
      </section>

      <section className="upload-list">
        <div className="upload-list__header">
          <h2>Uploads</h2>
          <button
            type="button"
            className="upload-list__refresh-icon"
            onClick={handleRefresh}
            disabled={isFetching}
            aria-label="Refresh uploads"
          >
            <svg
              className={`upload-list__refresh-svg${isFetching ? " upload-list__refresh-svg--spinning" : ""}`}
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <title>Refresh</title>
              <path d="M21 2v6h-6" />
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
              <path d="M3 22v-6h6" />
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
            </svg>
          </button>
          {refreshMessage && (
            <span className="upload-list__refresh-message">
              {refreshMessage}
            </span>
          )}
        </div>

        {isEmpty && (
          <p className="upload-list__empty-hint">
            Hexagone needs a GPX file to determine your areas of control.
            <br />
            <br />
            Upload one above to get started!
          </p>
        )}

        <div className="upload-list__table-container">
          <table className="upload-list__table">
            <thead>
              <tr>
                <th className="upload-list__th">Upload date</th>
                <th className="upload-list__th">Filename</th>
                <th className="upload-list__th">Status</th>
                <th className="upload-list__th">Download</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td
                    className="upload-list__td upload-list__td--empty"
                    colSpan={4}
                  >
                    Loading…
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td
                    className="upload-list__td upload-list__td--empty"
                    colSpan={4}
                  >
                    Failed to load uploads.
                  </td>
                </tr>
              ) : isEmpty ? (
                <tr>
                  <td
                    className="upload-list__td upload-list__td--empty"
                    colSpan={4}
                  >
                    No uploads found
                  </td>
                </tr>
              ) : (
                data?.items.map((upload: UploadResponse) => (
                  <tr key={upload.uid}>
                    <td className="upload-list__td">
                      {formatDate(upload.created_at)}
                    </td>
                    <td className="upload-list__td">
                      {upload.original_filename}
                    </td>
                    <td className="upload-list__td">
                      <StatusBadge status={upload.current_status} />
                    </td>
                    <td className="upload-list__td">
                      {upload.presigned_url ? (
                        <a
                          className="upload-list__link"
                          href={upload.presigned_url}
                          download={upload.original_filename}
                        >
                          Download
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {(data?.has_previous || data?.has_next) && (
          <div className="upload-list__pagination">
            <button
              type="button"
              className="upload-list__refresh"
              onClick={handlePrevious}
              disabled={!data?.has_previous}
            >
              Previous
            </button>
            <button
              type="button"
              className="upload-list__refresh"
              onClick={handleNext}
              disabled={!data?.has_next}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </>
  );
}
