import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import HealthStatus from "./HealthStatus";

vi.mock("@/hooks/useHealthCheck");

import { useHealthCheck } from "@/hooks/useHealthCheck";

const mockUseHealthCheck = vi.mocked(useHealthCheck);

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("HealthStatus", () => {
	test("shows Checking... while loading", () => {
		mockUseHealthCheck.mockReturnValue({ status: "loading", error: null });
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Checking...");
	});

	test("shows Connected on successful health check", () => {
		mockUseHealthCheck.mockReturnValue({ status: "connected", error: null });
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Connected");
	});

	test("shows Disconnected on failed health check", () => {
		mockUseHealthCheck.mockReturnValue({
			status: "disconnected",
			error: "Failed to fetch",
		});
		render(<HealthStatus />);
		expect(screen.getByRole("status")).toHaveTextContent("Disconnected");
	});
});
