import { Link } from "react-router-dom";
import { useListUploads } from "@/__generated__/backend-client/uploads";
import EmptyMap from "@/features/hexMap/EmptyMap";

export default function HexMap() {
  const { data, isPending, isError } = useListUploads();

  if (isPending) {
    // FIXME: Seeing loading states flash up twice: once on the protected route, and again when the query runs.
    // Ideally, we'd see this exactly once.
    return <div className="auth-loading">Loading</div>;
  }

  if (isError || !data) {
    throw new Error("Failed to load uploads");
  }

  if (data.items.length === 0) {
    return (
      <EmptyMap
        uploadsLink={
          <Link to="/uploads" className="button button--primary">
            Add your first upload
          </Link>
        }
      />
    );
  }

  return <div>TODO: Map with {data.items.length} uploads</div>;
}
