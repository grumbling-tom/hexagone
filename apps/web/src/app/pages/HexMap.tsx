import { Link } from "react-router-dom";
import { UploadStatusValue } from "@/__generated__/backend-client/backend.schemas";
import { useListUploads } from "@/__generated__/backend-client/uploads";
import EmptyMap from "@/features/hexMap/EmptyMap";

export default function HexMap() {
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
