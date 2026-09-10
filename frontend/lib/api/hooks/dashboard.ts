"use client";

import { useQuery } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type DashboardSummary = components["schemas"]["DashboardSummary"];

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async (): Promise<DashboardSummary> => {
      const { data, error } = await api.GET("/api/v1/dashboard/summary");
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}
