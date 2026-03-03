import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";

type Status = "loading" | "connected" | "disconnected";

export function useHealthCheck() {
	const [status, setStatus] = useState<Status>("loading");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const controller = new AbortController();

		fetch(`${API_BASE_URL}/health`, { signal: controller.signal })
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				return res.json();
			})
			.then((data) => {
				if (data?.status === "ok") {
					setStatus("connected");
				} else {
					setStatus("disconnected");
					setError("Unexpected response body");
				}
			})
			.catch((err) => {
				if (err.name === "AbortError") return;
				setStatus("disconnected");
				setError(err.message);
			});

		return () => controller.abort();
	}, []);

	return { status, error };
}
