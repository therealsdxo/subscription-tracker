"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ErrorState } from "@/components/ui/misc";
import { useLogin } from "@/lib/api/hooks/auth";
import { APP_NAME } from "@/lib/constants";

const schema = z.object({
  email: z.email("Enter a valid email"),
  password: z.string().min(1, "Enter your password"),
});
type FormValues = z.infer<typeof schema>;

function LoginForm() {
  const next = useSearchParams().get("next") ?? "/dashboard";
  const login = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit((values) => {
    login.mutate({ ...values, next });
  });
  const busy = isSubmitting || login.isPending;

  return (
    <div className="bg-bg flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-lg font-semibold tracking-tight">
          {APP_NAME}
        </h1>
        <p className="text-text-muted mb-6 text-center text-sm">Staff sign in</p>

        <form
          onSubmit={onSubmit}
          noValidate
          className="border-border bg-surface space-y-4 rounded-[var(--radius)] border p-5"
        >
          {login.isError ? <ErrorState message={login.error.message} /> : null}

          <Field label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              autoFocus
              {...register("email")}
            />
          </Field>
          <Field label="Password" htmlFor="password" error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
            />
          </Field>

          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
