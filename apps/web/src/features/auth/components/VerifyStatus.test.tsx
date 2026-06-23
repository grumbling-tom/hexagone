import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import VerifyStatus from "./VerifyStatus";

const newLink = <a href="/login">Request a new link</a>;

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

test("shows the countdown and a manual sign-in button", () => {
  const verify = vi.fn().mockResolvedValue({});

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );

  expect(screen.getByText(/redirecting you in 3s/i)).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /sign in now/i }),
  ).toBeInTheDocument();
});

test("the manual button consumes the token immediately", async () => {
  const verify = vi.fn().mockResolvedValue({});

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );
  fireEvent.click(screen.getByRole("button", { name: /sign in now/i }));

  await waitFor(() => expect(verify).toHaveBeenCalled());
  const submittedForm = verify.mock.calls[0][1] as FormData;
  expect(submittedForm.get("token")).toBe("a-token");
});

test("auto-submits once the countdown elapses", async () => {
  vi.useFakeTimers();
  const verify = vi.fn().mockResolvedValue({});

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );
  // Run the 3 one-second ticks; the last fires the auto-submit.
  await act(async () => {
    vi.advanceTimersByTime(3000);
  });
  // Flush the action dispatch (a transition) under real timers.
  vi.useRealTimers();
  await waitFor(() => expect(verify).toHaveBeenCalledTimes(1));
});

test("shows an error without consuming when there is no token", () => {
  const verify = vi.fn();

  render(
    <VerifyStatus token={null} verify={verify} requestNewLink={newLink} />,
  );

  expect(screen.getByText(/invalid or has expired/i)).toBeInTheDocument();
  expect(verify).not.toHaveBeenCalled();
});

test("shows an error when verify fails", async () => {
  const verify = vi.fn().mockResolvedValue({
    error: "This sign-in link is invalid or has expired.",
  });

  render(
    <VerifyStatus token="a-token" verify={verify} requestNewLink={newLink} />,
  );
  fireEvent.click(screen.getByRole("button", { name: /sign in now/i }));

  expect(
    await screen.findByText(/invalid or has expired/i),
  ).toBeInTheDocument();
});
