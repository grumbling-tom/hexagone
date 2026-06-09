import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type {
  PaginatedResultUploadResponse,
  UploadResponse,
} from "@/__generated__/backend-client/backend.schemas";
import {
  SortOrder,
  UploadSortField,
  UploadStatusValue,
} from "@/__generated__/backend-client/backend.schemas";
import {
  getListUploadsQueryKey,
  useListUploads,
} from "@/__generated__/backend-client/uploads";
import UploadForm from "@/features/uploads/UploadForm";
import UploadHelp from "@/features/uploads/UploadHelp";

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
  const [sortField, setSortField] = useState<UploadSortField>(
    UploadSortField.created_at,
  );
  const [sortOrder, setSortOrder] = useState<SortOrder>(SortOrder.desc);
  const queryClient = useQueryClient();

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

  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const queryParams = {
    page_size: 10,
    cursor: cursor ?? undefined,
    sort_field: sortField,
    sort_order: sortOrder,
  };
  const { data, isLoading, isError, isFetching } = useListUploads(queryParams);

  const handleSort = (field: UploadSortField) => {
    if (field === sortField) {
      setSortOrder((prev) =>
        prev === SortOrder.asc ? SortOrder.desc : SortOrder.asc,
      );
    } else {
      setSortField(field);
      setSortOrder(SortOrder.asc);
    }
    setCursor(null);
  };

  const sortIndicator = (field: UploadSortField) => {
    if (field !== sortField) return "";
    return sortOrder === SortOrder.asc ? " \u2191" : " \u2193";
  };

  const dataFingerprint = (d: PaginatedResultUploadResponse) =>
    d.items.map((i) => `${i.uid}:${i.current_status}`).join(",");

  const handleRefresh = async () => {
    setRefreshMessage(null);
    const before = data ? dataFingerprint(data) : null;
    await queryClient.invalidateQueries({
      queryKey: getListUploadsQueryKey(),
    });
    const after = queryClient.getQueryData<PaginatedResultUploadResponse>(
      getListUploadsQueryKey(queryParams),
    );
    if (before && after && dataFingerprint(after) === before) {
      setRefreshMessage("Already up to date.");
    }
  };

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: getListUploadsQueryKey() });
  };

  const handleNext = () => {
    if (data?.next_cursor) {
      setCursor(data.next_cursor);
    }
  };

  const handlePrevious = () => {
    if (data?.previous_cursor) {
      setCursor(data.previous_cursor);
    }
  };

  const isFirstPage = !data?.has_previous;
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
