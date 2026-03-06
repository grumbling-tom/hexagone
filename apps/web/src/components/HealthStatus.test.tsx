import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import HealthStatus from "./HealthStatus";

vi.mock("@/__generated__/backend-client/default/default", () => ({
	useHealthApiHealthGet: vi.fn(),
}));

import { useHealthApiHealthGet } from "@/__generated__/backend-client/default/default";

const mockUseHealthApiHealthGet = vi.mocked(useHealthApiHealthGet);

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("HealthStatus", () => {
	test("shows Checking... while loading", () => {
		mockUseHealthApiHealthGet.mockReturnValue({
			data: undefined,
			isLoading: true,
			isError: false,
		} as ReturnType<typeof useHealthApiHealthGet>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Checking...");
	});

	test("shows Connected on successful health check", () => {
		mockUseHealthApiHealthGet.mockReturnValue({
			data: { status: "ok" },
			isLoading: false,
			isError: false,
		} as ReturnType<typeof useHealthApiHealthGet>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Connected");
	});

	test("shows Disconnected on failed health check", () => {
		mockUseHealthApiHealthGet.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
		} as ReturnType<typeof useHealthApiHealthGet>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Disconnected");
	});
});
