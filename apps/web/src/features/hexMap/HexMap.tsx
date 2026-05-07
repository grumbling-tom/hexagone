import { useListAggregatedHexClaims } from "@/__generated__/backend-client/aggregated-hex-claims";
import { AggregateHexClaimBy } from "@/__generated__/backend-client/backend.schemas";

export default function HexMap() {
  const { data, isPending, isError } = useListAggregatedHexClaims({
    page_size: 1000,
    by: AggregateHexClaimBy.hex_cell,
  });

  if (isPending) {
    return <div className="auth-loading">Loading</div>;
  }

  if (isError || !data) {
    // TODO: Consider adding error boundaries to the app.
    throw new Error("Failed to load hex claims");
  }

  if (data.items.length === 0) {
    return <div>No hex claims found</div>;
  }

  return <div>TODO: Map with {data.items.length} hexes</div>;
}
