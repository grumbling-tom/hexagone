import { defineConfig } from "orval";

export default defineConfig({
	backend: {
		input: {
			target: "../backend/__generated__/openapi.json",
		},
		output: {
			target: "src/__generated__/backend-client",
			client: "react-query",
			mode: "tags",
			override: {
				mutator: {
					path: "./src/lib/fetch-client.ts",
					name: "fetchClient",
				},
			},
		},
	},
});
