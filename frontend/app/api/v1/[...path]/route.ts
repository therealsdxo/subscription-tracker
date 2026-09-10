import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import {
  clearSessionCookies,
  readAccessToken,
  readRefreshToken,
  refreshTokens,
  setSessionCookies,
} from "@/lib/server/auth";

type Ctx = { params: Promise<{ path: string[] }> };

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "content-encoding",
]);

async function forward(
  request: Request,
  targetPath: string,
  accessToken: string | undefined,
): Promise<Response> {
  const url = new URL(request.url);
  const headers = new Headers();
  for (const [k, v] of request.headers) {
    if (!HOP_BY_HOP.has(k.toLowerCase()) && k.toLowerCase() !== "host") headers.set(k, v);
  }
  if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);

  const method = request.method;
  const hasBody = method !== "GET" && method !== "HEAD";

  return fetch(`${env.apiUrl}/api/v1/${targetPath}${url.search}`, {
    method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
    redirect: "manual",
  });
}

async function proxy(request: Request, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params;
  const targetPath = path.join("/");

  let upstream = await forward(request, targetPath, await readAccessToken());
  let rotated: Awaited<ReturnType<typeof refreshTokens>> = null;

  if (upstream.status === 401) {
    rotated = await refreshTokens(await readRefreshToken());
    if (!rotated) {
      const res = NextResponse.json(
        { error: { code: "UNAUTHENTICATED", message: "Session expired" }, warnings: [] },
        { status: 401 },
      );
      clearSessionCookies(res);
      return res;
    }
    upstream = await forward(request, targetPath, rotated.access_token);
  }

  const res = new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
  });
  for (const [k, v] of upstream.headers) {
    if (!HOP_BY_HOP.has(k.toLowerCase())) res.headers.set(k, v);
  }
  if (rotated) setSessionCookies(res, rotated);
  return res;
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
