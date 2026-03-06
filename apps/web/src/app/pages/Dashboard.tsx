import HealthStatus from "@/components/HealthStatus";

export default function Dashboard() {
	return (
		<main className="dashboard">
			<h1>Dashboard</h1>
			<p>Welcome to Hexagone...</p>
			<HealthStatus />
		</main>
	);
}
