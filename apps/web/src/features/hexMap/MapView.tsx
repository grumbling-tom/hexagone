"use client";

import type { ReactNode } from "react";
import { UploadStatusValue } from "@/__generated__/backend-client/backend.schemas";
import { useListUploads } from "@/__generated__/backend-client/uploads";
import EmptyMap from "@/features/hexMap/EmptyMap";
import HexMap from "@/features/hexMap/HexMap";

// `uploadsLink` is supplied by the route (app/) so this feature stays free of
// routing imports — see CLAUDE.md → Frontend Import Rules (rule 3).
export default function MapView({ uploadsLink }: { uploadsLink: ReactNode }) {
  const { data, isPending, isError } = useListUploads({
    statuses: [UploadStatusValue.UPLOAD_SUCCESS],
  });

  if (isPending) {
    return <div className="auth-loading">Loading</div>;
  }

  if (isError || !data) {
    // TODO: Consider adding error boundaries to the app.
    throw new Error("Failed to load uploads");
  }

  if (data.items.length === 0) {
    return (
      <main className="page">
        <EmptyMap uploadsLink={uploadsLink} />
      </main>
    );
  }

  return <HexMap />;
}
