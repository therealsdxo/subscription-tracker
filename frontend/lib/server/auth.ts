import "server-only";

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE, REFRESH_COOKIE, env } from "@/lib/env";

const ACCESS_MAX_AGE = 60 * 20; // a little over the 15-min access TTL
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

type TokenPair = { access_token: string; refresh_token: string };

const baseCookie = {
  httpOnly: true,
  secure: env.cookieSecure,
  sameSite: "lax" as const,
  path: "/",
};

export function setSessionCookies(res: NextResponse, tokens: TokenPair): void {
  res.cookies.set(ACCESS_COOKIE, tokens.access_token, {
    ...baseCookie,
    maxAge: ACCESS_MAX_AGE,
  });
  res.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
    ...baseCookie,
    maxAge: REFRESH_MAX_AGE,
  });
}

export function clearSessionCookies(res: NextResponse): void {
  res.cookies.set(ACCESS_COOKIE, "", { ...baseCookie, maxAge: 0 });
  res.cookies.set(REFRESH_COOKIE, "", { ...baseCookie, maxAge: 0 });
}

export async function readAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}

export async function readRefreshToken(): Promise<string | undefined> {
  return (await cookies()).get(REFRESH_COOKIE)?.value;
}

/** Exchange the refresh token for a new pair. Returns null on failure. */
export async function refreshTokens(
  refreshToken: string | undefined,
): Promise<TokenPair | null> {
  if (!refreshToken) return null;
  const res = await fetch(`${env.apiUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as TokenPair;
}
