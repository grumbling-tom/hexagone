import { useGetHealth } from "@/__generated__/backend-client/health";

export default function HealthStatus() {
	const { data, isLoading, isError } = useGetHealth();

	if (isLoading) {
		return <output>Checking...</output>;
	}

	const connected = !isError && data?.status === "ok";

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
