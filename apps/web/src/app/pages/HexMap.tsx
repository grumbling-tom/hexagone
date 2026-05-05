import { useListAggregatedHexClaims } from "@/__generated__/backend-client/aggregated-hex-claims";
import { AggregateHexClaimBy } from "@/__generated__/backend-client/backend.schemas";
import MapEmptyState from "@/features/map/MapEmptyState";
import MapView from "@/features/map/MapView";

const PAGE_SIZE = 1_000;

export default function HexMap() {
  const { data, isLoading, isError } = useListAggregatedHexClaims({
    by: AggregateHexClaimBy.hex_cell,
    page_size: PAGE_SIZE,
  });

  let body: React.ReactNode;
  if (isLoading) {
    body = <MapEmptyState />;
  } else if (isError) {
    body = (
      <section className="map-error" aria-label="Map error">
        <p className="map-error__copy">
          We couldn't load your hexes. Refresh the page to try again.
        </p>
      </section>
    );
  } else {
    const claims = data?.items ?? [];
    body =
      claims.length === 0 ? <MapEmptyState /> : <MapView claims={claims} />;
  }

  return <main className="page map-page">{body}</main>;
}
