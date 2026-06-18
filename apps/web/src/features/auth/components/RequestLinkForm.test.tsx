import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import RequestLinkForm from "./RequestLinkForm";

test("renders an email field and no password field", () => {
  render(<RequestLinkForm action={vi.fn()} />);

  expect(screen.getByLabelText("Email")).toBeInTheDocument();
  expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
});

test("shows the check-your-email confirmation after a successful request", async () => {
  const action = vi.fn(async () => ({ sent: true }));
  const { container } = render(<RequestLinkForm action={action} />);

  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "user@example.com" },
  });
  const form = container.querySelector("form");
  if (!form) throw new Error("form not found");
  fireEvent.submit(form);

  expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
  expect(action).toHaveBeenCalled();
});

test("shows an error returned by the action", async () => {
  const action = vi.fn(async () => ({ error: "Something went wrong." }));
  const { container } = render(<RequestLinkForm action={action} />);

  const form = container.querySelector("form");
  if (!form) throw new Error("form not found");
  fireEvent.submit(form);

  expect(await screen.findByText("Something went wrong.")).toBeInTheDocument();
});
