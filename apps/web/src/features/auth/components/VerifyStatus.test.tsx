import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import VerifyStatus from "./VerifyStatus";

const newLink = <a href="/login">Request a new link</a>;

beforeEach(() => {
  vi.clearAllMocks();
});

test("fires verify on mount and shows the signing-in state", async () => {
  const verify = vi.fn().mockResolvedValue({});

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );

  expect(screen.getByText(/signing you in/i)).toBeInTheDocument();
  await waitFor(() => expect(verify).toHaveBeenCalledWith("a-token"));
});

test("shows an error when verify fails", async () => {
  const verify = vi.fn().mockResolvedValue({
    error: "This sign-in link is invalid or has expired.",
  });

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );

  expect(
    await screen.findByText(/invalid or has expired/i),
  ).toBeInTheDocument();
});

test("shows an error without calling verify when there is no token", () => {
  const verify = vi.fn();

  render(
    <VerifyStatus token={null} verify={verify} requestNewLink={newLink} />,
  );

  expect(screen.getByText(/invalid or has expired/i)).toBeInTheDocument();
  expect(verify).not.toHaveBeenCalled();
});
