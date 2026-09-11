"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Package = components["schemas"]["PackageOut"];
export type PackageStatus = components["schemas"]["PackageStatus"];
export type PackageCreateInput = components["schemas"]["PackageCreate"];
export type PackageUpdateInput = components["schemas"]["PackageUpdate"];

const KEY = ["packages"] as const;

export function usePackages(params: { status?: PackageStatus; page: number; page_size: number }) {
  return useQuery({
    queryKey: [...KEY, params],
    placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/packages", {
        params: { query: { status: params.status, page: params.page, page_size: params.page_size } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

/** Every ACTIVE package, unpaginated — for the subscription-create picker. */
export function useActivePackages() {
  return useQuery({
    queryKey: [...KEY, "active-all"],
    queryFn: async (): Promise<Package[]> => {
      const { data, error } = await api.GET("/api/v1/packages", {
        params: { query: { status: "ACTIVE", page: 1, page_size: 100 } },
      });
      if (error) throw new Error(errorMessage(error));
      return data.items;
    },
  });
}

export function usePackage(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, id],
    enabled: id != null,
    queryFn: async (): Promise<Package> => {
      const { data, error } = await api.GET("/api/v1/packages/{package_id}", {
        params: { path: { package_id: id! } },
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
  });
}

function useInvalidatePackages() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: KEY });
}

export function useCreatePackage() {
  const invalidate = useInvalidatePackages();
  return useMutation({
    mutationFn: async (input: PackageCreateInput) => {
      const { data, error } = await api.POST("/api/v1/packages", { body: input });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useUpdatePackage() {
  const invalidate = useInvalidatePackages();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: PackageUpdateInput }) => {
      const { data, error } = await api.PATCH("/api/v1/packages/{package_id}", {
        params: { path: { package_id: id } },
        body,
      });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useSetPackageStatus() {
  const invalidate = useInvalidatePackages();
  return useMutation({
    mutationFn: async ({ id, activate }: { id: number; activate: boolean }) => {
      const path = activate ? "/api/v1/packages/{package_id}/activate" : "/api/v1/packages/{package_id}/deactivate";
      const { data, error } = await api.POST(path, { params: { path: { package_id: id } } });
      if (error) throw new Error(errorMessage(error));
      return data;
    },
    onSuccess: invalidate,
  });
}

export function useDeletePackage() {
  const invalidate = useInvalidatePackages();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/v1/packages/{package_id}", {
        params: { path: { package_id: id } },
      });
      if (error) throw new Error(errorMessage(error));
    },
    onSuccess: invalidate,
  });
}
