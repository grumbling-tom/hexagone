import Link from "next/link";
import MapView from "@/features/hexMap/MapView";

export default function MapPage() {
  return (
    <MapView
      uploadsLink={
        <Link href="/uploads" className="button button--primary">
          Add your first upload
        </Link>
      }
    />
  );
}
