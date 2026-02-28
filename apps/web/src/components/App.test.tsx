import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";
import { AppRoutes } from "./App";

test("renders the dashboard at /", () => {
	render(
		<MemoryRouter initialEntries={["/"]}>
			<AppRoutes />
		</MemoryRouter>,
	);
	expect(
		screen.getByRole("heading", { name: "Dashboard" }),
	).toBeInTheDocument();
});

test("renders settings at /settings", () => {
	render(
		<MemoryRouter initialEntries={["/settings"]}>
			<AppRoutes />
		</MemoryRouter>,
	);
	expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
});
