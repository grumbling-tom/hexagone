import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import Settings from "./Settings";

test("renders settings page", () => {
	render(<Settings />);
	expect(screen.getByText("Manage your preferences.")).toBeInTheDocument();
});
