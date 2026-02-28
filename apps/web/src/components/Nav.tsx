import { NavLink } from "react-router-dom";

export default function Nav() {
	return (
		<nav style={{ display: "flex", gap: "1rem", padding: "1rem" }}>
			<NavLink to="/">Dashboard</NavLink>
			<NavLink to="/settings">Settings</NavLink>
		</nav>
	);
}
