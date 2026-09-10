"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api, errorMessage } from "@/lib/api/client";

export type CurrentUser = {
  id: number;
  email: string;
  full_name: string;
  role: "ADMIN" | "STAFF";
};

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async (): Promise<CurrentUser> => {
      const { data, error } = await api.GET("/api/v1/auth/me");
      if (error) throw new Error(errorMessage(error));
      return data as CurrentUser;
    },
    staleTime: 5 * 60_000,
  });
}

class LoginError extends Error {
  constructor(
    message: string,
    readonly retryAfter?: number,
  ) {
    super(message);
  }
}

export function useLogin() {
  const router = useRouter();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (input: { email: string; password: string; next?: string }) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: input.email, password: input.password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const retryAfter = Number(res.headers.get("Retry-After")) || undefined;
        throw new LoginError(
          res.status === 429
            ? `Too many attempts. Try again in ${retryAfter ?? 60}s.`
            : errorMessage(body, "Invalid email or password"),
          retryAfter,
        );
      }
      return input.next ?? "/dashboard";
    },
    onSuccess: (next) => {
      qc.clear();
      router.replace(next);
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST" });
    },
    onSuccess: () => {
      qc.clear();
      router.replace("/login");
    },
  });
}
