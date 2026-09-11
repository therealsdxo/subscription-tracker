"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Subscription = components["schemas"]["SubscriptionOut"];
export type SubscriptionDetail = components["schemas"]["SubscriptionDetail"];
export type SubscriptionStatus = components["schemas"]["SubscriptionStatus"];
export type SubscriptionCreateInput = components["schemas"]["SubscriptionCreate"];
export type SubscriptionRenewInput = components["schemas"]["SubscriptionRenew"];
export type SubscriptionUpdateInput = components["schemas"]["SubscriptionUpdate"];
export type SubscriptionEvent = components["schemas"]["SubscriptionEventOut"];
export type DeliveryOut = components["schemas"]["DeliveryOut"];
export type PlannedSkip = components["schemas"]["PlannedSkipOut"];
export type PlannedSkipCreateInput = components["schemas"]["PlannedSkipCreate"];
export type PaymentSummary = components["schemas"]["PaymentSummary"];
export type Payment = components["schemas"]["PaymentOut"];
export type Refund = components["schemas"]["RefundOut"];
export type PaymentCreateInput = components["schemas"]["PaymentCreate"];
export type RefundCreateInput = components["schemas"]["RefundCreate"];

export type SubscriptionListParams = {
  status?: SubscriptionStatus;
  customer_id?: number;
  expiring?: boolean;
  dues?: boolean;
  page: number;
  page_size: number;
};

const KEY = ["subscriptions"] as const;

export function useSubscriptions(params: SubscriptionListParams) {
  return useQuery({
    queryKey: [...KEY, params],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/subscriptions", {
        params: {
          query: {
            status: params.status,
            customer_id: params.customer_id,
            expiring: params.expiring,
            dues: params.dues,
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

export function useSubscription(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id],
    enabled: id != null,
    queryFn: async (): Promise<SubscriptionDetail> => {
      const { data, error } = await api.GET("/api/v1/subscriptions/{subscription_id}", {
        params: { path: { subscription_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

export function useSubscriptionEvents(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id, "events"],
    enabled: id != null,
    queryFn: async (): Promise<SubscriptionEvent[]> => {
      const { data, error } = await api.GET("/api/v1/subscriptions/{subscription_id}/events", {
        params: { path: { subscription_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

export function useSubscriptionDeliveries(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id, "deliveries"],
    enabled: id != null,
    queryFn: async (): Promise<DeliveryOut[]> => {
      const { data, error } = await api.GET("/api/v1/subscriptions/{subscription_id}/deliveries", {
        params: { path: { subscription_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

export function useSubscriptionSkips(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id, "skips"],
    enabled: id != null,
    queryFn: async (): Promise<PlannedSkip[]> => {
      const { data, error } = await api.GET("/api/v1/subscriptions/{subscription_id}/skips", {
        params: { path: { subscription_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

export function useSubscriptionPayments(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id, "payments"],
    enabled: id != null,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/subscriptions/{subscription_id}/payments", {
        params: { path: { subscription_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

function useInvalidateSubscriptions(id?: number) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: KEY });
    if (id != null) qc.invalidateQueries({ queryKey: [...KEY, id] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["customers"] });
  };
}

export function useCreateSubscription() {
  const invalidate = useInvalidateSubscriptions();
  return useMutation({
    mutationFn: async (input: SubscriptionCreateInput) => {
      const { data, error } = await api.POST("/api/v1/subscriptions", { body: input });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdateSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (body: SubscriptionUpdateInput) => {
      const { data, error } = await api.PATCH("/api/v1/subscriptions/{subscription_id}", {
        params: { path: { subscription_id: id } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function usePauseSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (reason: string) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/pause", {
        params: { path: { subscription_id: id } },
        body: { reason },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useResumeSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/resume", {
        params: { path: { subscription_id: id } },
        body: {},
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useExtendSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: { days?: number; new_end_date?: string; reason: string }) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/extend", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useCancelSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (reason: string) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/cancel", {
        params: { path: { subscription_id: id } },
        body: { reason },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useRenewSubscription(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: SubscriptionRenewInput) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/renew", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useAdjustMeals(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: { quantity: number; reason: string }) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/meal-adjustments", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useAddSkip(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: PlannedSkipCreateInput) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/skips", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useRemoveSkip(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (skipId: number) => {
      const { error } = await api.DELETE("/api/v1/subscriptions/{subscription_id}/skips/{skip_id}", {
        params: { path: { subscription_id: id, skip_id: skipId } },
      });
      if (error) throw new Error(errorMessage(error));
    },
    onSuccess: invalidate,
  });
}

export function useRecordPayment(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: PaymentCreateInput) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/payments", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useIssueRefund(id: number) {
  const invalidate = useInvalidateSubscriptions(id);
  return useMutation({
    mutationFn: async (input: RefundCreateInput) => {
      const { data, error } = await api.POST("/api/v1/subscriptions/{subscription_id}/refunds", {
        params: { path: { subscription_id: id } },
        body: input,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}
