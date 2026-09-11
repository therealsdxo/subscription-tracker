"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Payment = components["schemas"]["PaymentOut"];
export type PaymentMethod = components["schemas"]["PaymentMethod"];

export function usePayments(params: {
  subscription_id?: number;
  method?: PaymentMethod;
  date_from?: string;
  date_to?: string;
  page: number;
  page_size: number;
}) {
  return useQuery({
    queryKey: ["payments", params],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/payments", {
        params: {
          query: {
            subscription_id: params.subscription_id,
            method: params.method,
            date_from: params.date_from || undefined,
            date_to: params.date_to || undefined,
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
