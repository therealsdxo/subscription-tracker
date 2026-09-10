import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { setSessionCookies } from "@/lib/server/auth";

export async function POST(request: Request) {
  const body = await request.text();
  const upstream = await fetch(`${env.apiUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
    cache: "no-store",
  });

  const payload = await upstream.json().catch(() => ({}));

  if (!upstream.ok) {
    // Pass the API's error envelope + status straight through (401, 429, …).
    const res = NextResponse.json(payload, { status: upstream.status });
    const retryAfter = upstream.headers.get("retry-after");
    if (retryAfter) res.headers.set("Retry-After", retryAfter);
    return res;
  }

  const res = NextResponse.json({ ok: true });
  setSessionCookies(res, payload);
  return res;
}
