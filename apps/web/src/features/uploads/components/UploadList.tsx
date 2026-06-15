"use client";

import { useRef, useState, useTransition } from "react";
import type {
  CreateUploadRequest,
  ListUploadsParams,
  PaginatedResultUploadResponse,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";
import {
  SortOrder,
  UploadSortField,
  UploadStatusValue,
} from "@/__generated__/backend-client/backend.schemas";
import UploadForm from "@/features/uploads/components/UploadForm";
import UploadHelp from "@/features/uploads/components/UploadHelp";

const PAGE_SIZE = 10;

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

function dataFingerprint(d: PaginatedResultUploadResponse) {
  return d.items.map((i) => `${i.uid}:${i.current_status}`).join(",");
}

interface UploadListProps {
  // Initial page fetched server-side by the route (RSC), so the table renders
  // populated on first paint with no client round-trip.
  initialUploads: PaginatedResultUploadResponse;
  // Server actions supplied by the route for interactive reads/writes.
  fetchUploads: (
    params: ListUploadsParams,
  ) => Promise<PaginatedResultUploadResponse>;
  requestUpload: (data: CreateUploadRequest) => Promise<UploadResponse>;
}

export default function UploadList({
  initialUploads,
  fetchUploads,
  requestUpload,
}: UploadListProps) {
  const [data, setData] = useState(initialUploads);
  const [sortField, setSortField] = useState<UploadSortField>(
    UploadSortField.created_at,
  );
  const [sortOrder, setSortOrder] = useState<SortOrder>(SortOrder.desc);
  // Cursor that produced the current page (used to reload the same page).
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [isError, setIsError] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // TODO: No need for state here.
  // Alternatives are CSS :hover tooltips (but they don't work on mobile)
  // or a dedicated info icon that opens a tooltip on click.
  const [tooltipPos, setTooltipPos] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const infoIconRef = useRef<HTMLSpanElement>(null);

  const showTooltip = () => {
    if (infoIconRef.current) {
      const rect = infoIconRef.current.getBoundingClientRect();
      setTooltipPos({
        top: rect.bottom + 8,
        left: rect.left + rect.width / 2,
      });
    }
  };

  const hideTooltip = () => {
    setTooltipPos(null);
  };

  // Fetch a page via the server action and swap it into local state. React
  // Query used to own this; now the route owns the data and we drive reads
  // imperatively through the passed-in action.
  const load = (params: ListUploadsParams) => {
    setRefreshMessage(null);
    startTransition(async () => {
      try {
        const result = await fetchUploads(params);
        setData(result);
        setIsError(false);
        setCursor(params.cursor ?? undefined);
      } catch {
        setIsError(true);
      }
    });
  };

  const handleSort = (field: UploadSortField) => {
    const nextOrder =
      field === sortField
        ? sortOrder === SortOrder.asc
          ? SortOrder.desc
          : SortOrder.asc
        : SortOrder.asc;
    setSortField(field);
    setSortOrder(nextOrder);
    // Changing the sort returns to the first page.
    load({ page_size: PAGE_SIZE, sort_field: field, sort_order: nextOrder });
  };

  const sortIndicator = (field: UploadSortField) => {
    if (field !== sortField) return "";
    return sortOrder === SortOrder.asc ? " ↑" : " ↓";
  };

  const handleRefresh = () => {
    setRefreshMessage(null);
    const before = dataFingerprint(data);
    startTransition(async () => {
      try {
        const result = await fetchUploads({
          page_size: PAGE_SIZE,
          cursor,
          sort_field: sortField,
          sort_order: sortOrder,
        });
        setData(result);
        setIsError(false);
        if (dataFingerprint(result) === before) {
          setRefreshMessage("Already up to date.");
        }
      } catch {
        setIsError(true);
      }
    });
  };

  const handleUploadComplete = () => {
    load({
      page_size: PAGE_SIZE,
      cursor,
      sort_field: sortField,
      sort_order: sortOrder,
    });
  };

  const handleNext = () => {
    if (data.next_cursor) {
      load({
        page_size: PAGE_SIZE,
        cursor: data.next_cursor,
        sort_field: sortField,
        sort_order: sortOrder,
      });
    }
  };

  const handlePrevious = () => {
    if (data.previous_cursor) {
      load({
        page_size: PAGE_SIZE,
        cursor: data.previous_cursor,
        sort_field: sortField,
        sort_order: sortOrder,
      });
    }
  };

  const isEmpty = !data.has_previous && data.items.length === 0;

  return (
    <>
      <section className="upload-section">
        <h2>Upload a GPX file</h2>
        <UploadForm
          requestUpload={requestUpload}
          onUploadComplete={handleUploadComplete}
        />
        <UploadHelp className="upload-section__help" />
      </section>

      <section className="upload-list">
        <div className="upload-list__header">
          <h2>Uploads</h2>
          <button
            type="button"
            className="upload-list__refresh-icon"
            onClick={handleRefresh}
            disabled={isPending}
            aria-label="Refresh uploads"
          >
            <svg
              className={`upload-list__refresh-svg${isPending ? " upload-list__refresh-svg--spinning" : ""}`}
              viewBox="0 0 24 24"
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
                <th
                  className="upload-list__th upload-list__th--sortable"
                  onClick={() => handleSort(UploadSortField.created_at)}
                >
                  Upload date{sortIndicator(UploadSortField.created_at)}
                </th>
                <th
                  className="upload-list__th upload-list__th--sortable"
                  onClick={() => handleSort(UploadSortField.original_filename)}
                >
                  Filename{sortIndicator(UploadSortField.original_filename)}
                </th>
                <th className="upload-list__th">
                  <span className="upload-list__th-with-info">
                    Status
                    <span
                      role="note"
                      className="upload-list__info"
                      onMouseEnter={showTooltip}
                      onMouseLeave={hideTooltip}
                    >
                      <span
                        ref={infoIconRef}
                        className="upload-list__info-icon"
                      >
                        i
                      </span>
                      <span
                        className="upload-list__info-tooltip"
                        style={
                          tooltipPos
                            ? {
                                display: "flex",
                                top: tooltipPos.top,
                                left: tooltipPos.left,
                                transform: "translateX(-50%)",
                              }
                            : undefined
                        }
                      >
                        <span className="upload-list__info-row">
                          Larger GPX files can take a little while to process.
                          <br />
                          This column indicates each upload's current status.
                        </span>
                        <span className="upload-list__info-row">
                          <StatusBadge
                            status={UploadStatusValue.UPLOAD_RECEIVED}
                          />
                          File received, being analysed
                        </span>
                        <span className="upload-list__info-row">
                          <StatusBadge
                            status={UploadStatusValue.UPLOAD_SUCCESS}
                          />
                          Analysis complete
                        </span>
                        <span className="upload-list__info-row">
                          <StatusBadge
                            status={UploadStatusValue.UPLOAD_INVALID}
                          />
                          File could not be processed
                        </span>
                      </span>
                    </span>
                  </span>
                </th>
                <th className="upload-list__th">Download</th>
              </tr>
            </thead>
            <tbody>
              {isError ? (
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
                data.items.map((upload: UploadResponse) => (
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

        {(data.has_previous || data.has_next) && (
          <div className="upload-list__pagination">
            <button
              type="button"
              className="upload-list__refresh"
              onClick={handlePrevious}
              disabled={!data.has_previous || isPending}
            >
              Previous
            </button>
            <button
              type="button"
              className="upload-list__refresh"
              onClick={handleNext}
              disabled={!data.has_next || isPending}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </>
  );
}
