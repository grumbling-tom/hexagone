import { useGetHealth } from "@/__generated__/backend-client/health";

export default function HealthStatus() {
  const { data, isLoading, isError } = useGetHealth();

  if (isLoading) {
    return <output>Checking...</output>;
  }

  const connected = !isError && data?.status === "ok";

  return (
    <output className="health-status">
      <span
        aria-hidden="true"
        className={`health-status__dot health-status__dot--${connected ? "connected" : "disconnected"}`}
      />
      {connected ? "Connected" : "Disconnected"}
    </output>
  );
}
