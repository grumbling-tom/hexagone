import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import HealthStatus from "./HealthStatus";

vi.mock("@/__generated__/backend-client/default/default", () => ({
	useGetHealth: vi.fn(),
}));

import { useGetHealth } from "@/__generated__/backend-client/default/default";

const mockUseGetHealth = vi.mocked(useGetHealth);

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("HealthStatus", () => {
	test("shows Checking... while loading", () => {
		mockUseGetHealth.mockReturnValue({
			data: undefined,
			isLoading: true,
			isError: false,
		} as ReturnType<typeof useGetHealth>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Checking...");
	});

	test("shows Connected on successful health check", () => {
		mockUseGetHealth.mockReturnValue({
			data: { status: "ok" },
			isLoading: false,
			isError: false,
		} as ReturnType<typeof useGetHealth>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Connected");
	});

	test("shows Disconnected on failed health check", () => {
		mockUseGetHealth.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
		} as ReturnType<typeof useGetHealth>);
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Disconnected");
	});
});
