import Link from "next/link";
import { listAggregatedHexClaims } from "@/__generated__/backend-client/aggregated-hex-claims";
import {
  AggregateHexClaimBy,
  UploadStatusValue,
} from "@/__generated__/backend-client/backend.schemas";
import { listUploads } from "@/__generated__/backend-client/uploads";
import EmptyMap from "@/features/hexMap/EmptyMap";
import HexMap from "@/features/hexMap/HexMap";

export default async function MapPage() {
  const uploads = await listUploads({
    statuses: [UploadStatusValue.UPLOAD_SUCCESS],
  });

  if (uploads.items.length === 0) {
    return (
      <main className="page">
        <EmptyMap
          uploadsLink={
            <Link href="/uploads" className="button button--primary">
              Add your first upload
            </Link>
          }
        />
      </main>
    );
  }

  const claims = await listAggregatedHexClaims({
    page_size: 1000,
    by: AggregateHexClaimBy.hex_cell,
  });

  return <HexMap claims={claims.items} />;
}
