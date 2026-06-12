import { NextRequest } from "next/server";
import { expect, test } from "vitest";
import { middleware } from "./middleware";

function request(path: string, cookie?: string) {
  const req = new NextRequest(new URL(`http://localhost${path}`));
  if (cookie) req.cookies.set("sessionid", cookie);
  return req;
}

test("redirects to /login when the session cookie is missing", () => {
  const res = middleware(request("/map"));
  expect(res.status).toBe(307);
  expect(new URL(res.headers.get("location") ?? "").pathname).toBe("/login");
});

test("passes through when the session cookie is present", () => {
  const res = middleware(request("/map", "some-session-id"));
  // NextResponse.next() carries no redirect Location header.
  expect(res.headers.get("location")).toBeNull();
});
