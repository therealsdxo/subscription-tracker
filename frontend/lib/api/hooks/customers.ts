"use client";

import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Customer = components["schemas"]["CustomerOut"];
export type CustomerDetail = components["schemas"]["CustomerDetail"];
export type CustomerPage = components["schemas"]["Page_CustomerOut_"];
export type Address = components["schemas"]["AddressOut"];
export type CustomerCreateInput = components["schemas"]["CustomerCreate"];
export type CustomerUpdateInput = components["schemas"]["CustomerUpdate"];
export type AddressCreateInput = components["schemas"]["AddressCreate"];
export type AddressUpdateInput = components["schemas"]["AddressUpdate"];

export type CustomerListParams = {
  q?: string;
  is_active?: boolean;
  page: number;
  page_size: number;
};

const KEY = ["customers"] as const;

export function useCustomers(params: CustomerListParams) {
  return useQuery({
    queryKey: [...KEY, params],
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

export function useCustomer(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id],
    enabled: id != null,
    queryFn: async (): Promise<CustomerDetail> => {
      const { data, error } = await api.GET("/api/v1/customers/{customer_id}", {
        params: { path: { customer_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

/** All active customers, for pickers (e.g. subscription create). */
export function useCustomerSearch(q: string) {
  return useQuery({
    queryKey: [...KEY, "search", q],
    enabled: q.trim().length > 0,
    queryFn: async (): Promise<Customer[]> => {
      const { data, error } = await api.GET("/api/v1/customers", {
        params: { query: { q, is_active: true, page: 1, page_size: 10 } },
      });
      if (error) throw new Error(errorMessage(error));
      return data.items;
    },
  });
}

/** Batched lookup for tables that only carry a customer_id (subscriptions,
 * payments). Each id is cached individually, so repeats across pages are free. */
export function useCustomersByIds(ids: number[]): Map<number, Customer> {
  const unique = Array.from(new Set(ids));
  const results = useQueries({
    queries: unique.map((id) => ({
      queryKey: [...KEY, id],
      queryFn: async (): Promise<CustomerDetail> => {
        const { data, error } = await api.GET("/api/v1/customers/{customer_id}", {
          params: { path: { customer_id: id } },
        });
        if (error) throw new Error(errorMessage(error));
        return data;
      },
      staleTime: 60_000,
    })),
  });
  const map = new Map<number, Customer>();
  results.forEach((r, i) => {
    if (r.data) map.set(unique[i], r.data);
  });
  return map;
}

function useInvalidateCustomers() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: KEY });
}

export function useCreateCustomer() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async (input: CustomerCreateInput) => {
      const { data, error } = await api.POST("/api/v1/customers", { body: input });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdateCustomer() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: CustomerUpdateInput }) => {
      const { data, error } = await api.PATCH("/api/v1/customers/{customer_id}", {
        params: { path: { customer_id: id } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useSetCustomerActive() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async (
      input: { id: number; activate: true } | { id: number; activate: false; reason: string },
    ) => {
      if (input.activate) {
        const { data, error } = await api.POST("/api/v1/customers/{customer_id}/reactivate", {
          params: { path: { customer_id: input.id } },
        });
        if (error) throw new Error(errorMessage(error));
        return data;
      }
      const { data, error } = await api.POST("/api/v1/customers/{customer_id}/deactivate", {
        params: { path: { customer_id: input.id } },
        body: { reason: input.reason },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useAddAddress() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async ({ customerId, body }: { customerId: number; body: AddressCreateInput }) => {
      const { data, error } = await api.POST("/api/v1/customers/{customer_id}/addresses", {
        params: { path: { customer_id: customerId } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdateAddress() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async ({
      customerId,
      addressId,
      body,
    }: {
      customerId: number;
      addressId: number;
      body: AddressUpdateInput;
    }) => {
      const { data, error } = await api.PATCH("/api/v1/customers/{customer_id}/addresses/{address_id}", {
        params: { path: { customer_id: customerId, address_id: addressId } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useRemoveAddress() {
  const invalidate = useInvalidateCustomers();
  return useMutation({
    mutationFn: async ({ customerId, addressId }: { customerId: number; addressId: number }) => {
      const { error } = await api.DELETE("/api/v1/customers/{customer_id}/addresses/{address_id}", {
        params: { path: { customer_id: customerId, address_id: addressId } },
      });
      if (error) throw new Error(errorMessage(error));
    },
    onSuccess: invalidate,
  });
}
