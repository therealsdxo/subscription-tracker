"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type DeliveryRow = components["schemas"]["DeliveryListRow"];
export type DeliveryStatus = components["schemas"]["DeliveryStatus"];
export type TimeSlot = components["schemas"]["TimeSlot"];
export type DeliveryUpdateInput = components["schemas"]["DeliveryUpdate"];
export type GenerateResult = components["schemas"]["GenerateResult"];

const KEY = ["deliveries"] as const;

export function useDeliveries(params: {
  date: string;
  status?: DeliveryStatus;
  area?: string;
  time_slot?: TimeSlot;
  page: number;
  page_size: number;
}) {
  return useQuery({
    queryKey: [...KEY, params],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/deliveries", {
        params: {
          query: {
            date: params.date,
            status: params.status,
            area: params.area || undefined,
            time_slot: params.time_slot,
            page: params.page,
            page_size: params.page_size,
          },
        },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

function useInvalidateDeliveries() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: KEY });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["subscriptions"] });
  };
}

export function useGenerateDeliveries() {
  const invalidate = useInvalidateDeliveries();
  return useMutation({
    mutationFn: async (date: string): Promise<GenerateResult> => {
      const { data, error } = await api.POST("/api/v1/deliveries/generate", { body: { date } });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdateDelivery() {
  const invalidate = useInvalidateDeliveries();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: DeliveryUpdateInput }) => {
      const { data, error } = await api.PATCH("/api/v1/deliveries/{delivery_id}", {
        params: { path: { delivery_id: id } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useReverseDelivery() {
  const invalidate = useInvalidateDeliveries();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const { data, error } = await api.POST("/api/v1/deliveries/{delivery_id}/reverse", {
        params: { path: { delivery_id: id } },
        body: { reason },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}
