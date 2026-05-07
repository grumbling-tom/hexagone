import { Link } from "react-router-dom";
import EmptyMap from "@/features/hexMap/EmptyMap";

export default function HexMap() {
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
