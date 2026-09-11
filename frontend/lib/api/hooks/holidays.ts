"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Holiday = components["schemas"]["HolidayOut"];
export type HolidayCreateInput = components["schemas"]["HolidayCreate"];

const KEY = ["holidays"] as const;

export function useHolidays() {
  return useQuery({
    queryKey: KEY,
    queryFn: async (): Promise<Holiday[]> => {
      const { data, error } = await api.GET("/api/v1/holidays", { params: { query: {} } });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

export function useAddHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: HolidayCreateInput) => {
      const { data, error } = await api.POST("/api/v1/holidays", { body: input });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRemoveHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/v1/holidays/{holiday_id}", {
        params: { path: { holiday_id: id } },
      });
      if (error) throw new Error(errorMessage(error));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
