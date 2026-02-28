import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useHealthCheck } from "./useHealthCheck";

afterEach(() => {
	vi.restoreAllMocks();
});

describe("useHealthCheck", () => {
	test("returns loading initially", () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() => new Promise(() => {})),
		);
		const { result } = renderHook(() => useHealthCheck());
		expect(result.current.status).toBe("loading");
		expect(result.current.error).toBeNull();
	});

	test("returns connected on 200 with ok status", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() =>
				Promise.resolve({
					ok: true,
					json: () => Promise.resolve({ status: "ok" }),
				}),
			),
		);
		const { result } = renderHook(() => useHealthCheck());
		await waitFor(() => expect(result.current.status).toBe("connected"));
		expect(result.current.error).toBeNull();
	});

	test("returns disconnected on network error", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
		);
		const { result } = renderHook(() => useHealthCheck());
		await waitFor(() => expect(result.current.status).toBe("disconnected"));
		expect(result.current.error).toBe("Failed to fetch");
	});

	test("returns disconnected on non-200 response", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() =>
				Promise.resolve({
					ok: false,
					status: 500,
					json: () => Promise.resolve({}),
				}),
			),
		);
		const { result } = renderHook(() => useHealthCheck());
		await waitFor(() => expect(result.current.status).toBe("disconnected"));
		expect(result.current.error).toBe("HTTP 500");
	});

	test("returns disconnected on unexpected body", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() =>
				Promise.resolve({
					ok: true,
					json: () => Promise.resolve({ status: "not-ok" }),
				}),
			),
		);
		const { result } = renderHook(() => useHealthCheck());
		await waitFor(() => expect(result.current.status).toBe("disconnected"));
		expect(result.current.error).toBe("Unexpected response body");
	});

	test("cleans up via AbortController on unmount", () => {
		const abortSpy = vi.fn();
		vi.stubGlobal(
			"AbortController",
			class {
				signal = "mock-signal";
				abort = abortSpy;
			},
		);
		vi.stubGlobal(
			"fetch",
			vi.fn(() => new Promise(() => {})),
		);

		const { unmount } = renderHook(() => useHealthCheck());
		expect(abortSpy).not.toHaveBeenCalled();
		unmount();
		expect(abortSpy).toHaveBeenCalled();
	});
});
