import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuthContext } from "@/lib/auth";

export default function Nav() {
  const navigate = useNavigate();
  const { signOut } = useAuthContext();
  const [isPending, setIsPending] = useState(false);

  async function handleLogout() {
    setIsPending(true);
    await signOut();
    navigate("/login");
  }

  return (
    <nav className="nav">
      <NavLink to="/">Dashboard</NavLink>
      <NavLink to="/settings">Settings</NavLink>
      <button
        className="button nav__logout"
        type="button"
        onClick={() => void handleLogout()}
        disabled={isPending}
      >
        Log out
      </button>
    </nav>
  );
}
