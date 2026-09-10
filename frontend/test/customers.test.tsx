import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CustomersPage from "@/app/(app)/customers/page";
import { api } from "@/lib/api/client";

import { renderWithClient } from "./utils";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, api: { GET: vi.fn() } };
});

const page = (items: unknown[], total: number) => ({
  data: { items, total, page: 1, page_size: 25 },
  error: undefined,
});

describe("CustomersPage", () => {
  beforeEach(() => vi.resetAllMocks());

  it("renders a row per customer and the pagination footer", async () => {
    vi.mocked(api.GET).mockResolvedValue(
      page(
        [
          {
            id: 1,
            customer_code: "CUST-000001",
            name: "Asha Rao",
            phone: "999",
            is_active: true,
          },
          {
            id: 2,
            customer_code: "CUST-000002",
            name: "Bhavna Iyer",
            phone: "888",
            is_active: false,
          },
        ],
        2,
      ) as never,
    );

    renderWithClient(<CustomersPage />);

    await waitFor(() => expect(screen.getByText("Asha Rao")).toBeInTheDocument());
    expect(screen.getByText("Bhavna Iyer")).toBeInTheDocument();
    expect(screen.getByText("CUST-000002")).toBeInTheDocument();
    expect(screen.getByText("1–2 of 2")).toBeInTheDocument();
  });

  it("passes the search text into the query", async () => {
    vi.mocked(api.GET).mockResolvedValue(page([], 0) as never);
    renderWithClient(<CustomersPage />);

    await userEvent.type(screen.getByPlaceholderText("Search by name…"), "asha");

    await waitFor(() => {
      const lastCall = vi.mocked(api.GET).mock.calls.at(-1);
      expect(lastCall?.[1]).toMatchObject({ params: { query: { q: "asha" } } });
    });
  });
});
