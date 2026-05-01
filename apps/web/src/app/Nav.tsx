import { useQueryClient } from "@tanstack/react-query";
import { NavLink, useNavigate } from "react-router-dom";
import { useDeleteCurrentSession } from "@/__generated__/backend-client/user-sessions";

export default function Nav() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const logout = useDeleteCurrentSession({
    mutation: {
      onSuccess: () => {
        queryClient.clear();
        navigate("/login");
      },
    },
  });

  return (
    <nav className="nav">
      <NavLink to="/" end>
        Map
      </NavLink>
      <NavLink to="/uploads">Uploads</NavLink>
      <button
        className="button nav__logout"
        type="button"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        Log out
      </button>
    </nav>
  );
}
