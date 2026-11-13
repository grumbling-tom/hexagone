// @vitest-environment node
import { afterEach, expect, test, vi } from "vitest";
import { ApiError, HttpStatus } from "@/lib/fetch-client";
import { POST } from "./route";

const createUploadProcessingJob = vi.hoisted(() => vi.fn());

vi.mock("@/__generated__/backend-client/upload-processing-jobs", () => ({
  createUploadProcessingJob,
}));

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

test("forwards the parsed body and Bearer header to the backend client", async () => {
  createUploadProcessingJob.mockResolvedValue(undefined);

  const events = [{ eventName: "OBJECT_CREATED_PUT", object: { key: "a" } }];
  const response = await POST(
    webhookRequest({
      body: JSON.stringify({ events }),
      headers: { authorization: "Bearer s3cr3t" },
    }),
  );

  expect(response.status).toBe(202);
  expect(createUploadProcessingJob).toHaveBeenCalledOnce();
  expect(createUploadProcessingJob).toHaveBeenCalledWith(
    { events },
    { headers: { authorization: "Bearer s3cr3t" } },
  );
});

test("passes the backend's status through (e.g. 401 on a bad secret)", async () => {
  createUploadProcessingJob.mockRejectedValue(
    new ApiError(HttpStatus.UNAUTHORIZED, {
      detail: "Invalid notification secret",
    }),
  );

  const response = await POST(webhookRequest());

  expect(response.status).toBe(401);
});

test("returns 502 when the backend is unreachable", async () => {
  createUploadProcessingJob.mockRejectedValue(new Error("ECONNREFUSED"));

  const response = await POST(webhookRequest());

  expect(response.status).toBe(502);
});
