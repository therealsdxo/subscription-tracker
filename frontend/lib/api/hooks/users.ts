"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type User = components["schemas"]["UserOut"];
export type UserCreateInput = components["schemas"]["UserCreate"];
export type UserUpdateInput = components["schemas"]["UserUpdate"];

const KEY = ["users"] as const;

export function useUsers(params: { page: number; page_size: number }) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/users", {
        params: { query: { page: params.page, page_size: params.page_size } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

function useInvalidateUsers() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: KEY });
}

export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: async (input: UserCreateInput) => {
      const { data, error } = await api.POST("/api/v1/users", { body: input });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: UserUpdateInput }) => {
      const { data, error } = await api.PATCH("/api/v1/users/{user_id}", {
        params: { path: { user_id: id } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useDeactivateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.POST("/api/v1/users/{user_id}/deactivate", {
        params: { path: { user_id: id } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}
