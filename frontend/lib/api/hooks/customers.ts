"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Customer = components["schemas"]["CustomerOut"];
export type CustomerPage = components["schemas"]["Page_CustomerOut_"];

export type CustomerListParams = {
  q?: string;
  is_active?: boolean;
  page: number;
  page_size: number;
};

export function useCustomers(params: CustomerListParams) {
  return useQuery({
    queryKey: ["customers", params],
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<CustomerPage> => {
      const { data, error } = await api.GET("/api/v1/customers", {
        params: {
          query: {
            q: params.q || undefined,
            is_active: params.is_active,
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
