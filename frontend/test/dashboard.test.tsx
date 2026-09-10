import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(app)/dashboard/page";
import { api } from "@/lib/api/client";

import { renderWithClient } from "./utils";

vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, api: { GET: vi.fn() } };
});

describe("DashboardPage", () => {
  beforeEach(() => vi.resetAllMocks());

  it("renders the five stat tiles from the API response", async () => {
    vi.mocked(api.GET).mockResolvedValue({
      data: {
        active_subscriptions: 12,
        todays_meals_planned: 30,
        delivered_today: 8,
        expiring_soon: 3,
        outstanding_dues_total: "4500.00",
      },
      error: undefined,
    } as never);

    renderWithClient(<DashboardPage />);

    await waitFor(() => expect(screen.getByText("12")).toBeInTheDocument());
    expect(screen.getByText("Active subscriptions")).toBeInTheDocument();
    expect(screen.getByText("₹4500.00")).toBeInTheDocument();
    expect(screen.getByText("Delivered today")).toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    vi.mocked(api.GET).mockResolvedValue({
      data: undefined,
      error: { error: { code: "INTERNAL_ERROR", message: "boom" } },
    } as never);

    renderWithClient(<DashboardPage />);
    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
  });
});
