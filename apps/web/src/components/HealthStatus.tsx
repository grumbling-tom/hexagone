import { useHealthCheck } from "@/hooks/useHealthCheck";

export default function HealthStatus() {
	const { status } = useHealthCheck();

	if (status === "loading") {
		return <output>Checking...</output>;
	}

	const connected = status === "connected";

	return (
		<output
			style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}
		>
			<span
				aria-hidden="true"
				style={{
					width: "0.5rem",
					height: "0.5rem",
					borderRadius: "50%",
					backgroundColor: connected ? "green" : "red",
				}}
			/>
			{connected ? "Connected" : "Disconnected"}
		</output>
	);
}
