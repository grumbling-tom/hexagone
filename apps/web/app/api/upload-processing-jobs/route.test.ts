// @vitest-environment node
import { afterEach, expect, test, vi } from "vitest";
import { env } from "@/config/env";
import { POST } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
});

function webhookRequest(init?: RequestInit): Request {
  return new Request("https://hexagone.example/api/upload-processing-jobs", {
    method: "POST",
    body: JSON.stringify({ events: [] }),
    ...init,
  });
}

test("forwards the webhook to the backend, keeping the Bearer header and body", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 202 }));

  const body = JSON.stringify({
    events: [{ eventName: "OBJECT_CREATED_PUT" }],
  });
  const response = await POST(
    webhookRequest({
      body,
      headers: { authorization: "Bearer s3cr3t" },
    }),
  );

  expect(response.status).toBe(202);
  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, requestInit] = fetchMock.mock.calls[0];
  expect((url as URL).toString()).toBe(
    `${env.BACKEND_ORIGIN}/api/v1/upload-processing-jobs`,
  );
  expect(requestInit?.method).toBe("POST");
  expect(requestInit?.body).toBe(body);
  expect(new Headers(requestInit?.headers).get("authorization")).toBe(
    "Bearer s3cr3t",
  );
});

test("passes the backend's status through (e.g. 401 on a bad secret)", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(null, { status: 401 }),
  );

  const response = await POST(webhookRequest());

  expect(response.status).toBe(401);
});

test("returns 502 when the backend is unreachable", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("ECONNREFUSED"));

  const response = await POST(webhookRequest());

  expect(response.status).toBe(502);
});
