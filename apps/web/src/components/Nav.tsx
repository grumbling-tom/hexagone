import { NavLink } from "react-router-dom";

export default function Nav() {
  return (
    <nav className="nav">
      <NavLink to="/">Dashboard</NavLink>
      <NavLink to="/settings">Settings</NavLink>
    </nav>
  );
}
