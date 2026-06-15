import {
  SortOrder,
  UploadSortField,
} from "@/__generated__/backend-client/backend.schemas";
import { listUploads } from "@/__generated__/backend-client/uploads";
import UploadList from "@/features/uploads/components/UploadList";
import { fetchUploads, requestUpload } from "@/features/uploads/server/uploads";

export default async function UploadsPage() {
  const initialUploads = await listUploads({
    page_size: 10,
    sort_field: UploadSortField.created_at,
    sort_order: SortOrder.desc,
  });

  return (
    <main className="page">
      <UploadList
        initialUploads={initialUploads}
        fetchUploads={fetchUploads}
        requestUpload={requestUpload}
      />
    </main>
  );
}
