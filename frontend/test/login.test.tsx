import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/(auth)/login/page";

import { renderWithClient } from "./utils";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    replace.mockReset();
  });

  it("validates the email field", async () => {
    renderWithClient(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
  });

  it("redirects on a successful login", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    renderWithClient(<LoginPage />);

    await userEvent.type(screen.getByLabelText("Email"), "admin@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "supersecret123");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("surfaces a 429 rate-limit message", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "RATE_LIMITED", message: "x" } }), {
        status: 429,
        headers: { "Retry-After": "42" },
      }),
    );
    renderWithClient(<LoginPage />);

    await userEvent.type(screen.getByLabelText("Email"), "admin@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText(/Too many attempts/)).toBeInTheDocument();
  });
});
