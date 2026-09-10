import { NextResponse } from "next/server";

import {
  clearSessionCookies,
  readRefreshToken,
  refreshTokens,
  setSessionCookies,
} from "@/lib/server/auth";

export async function POST() {
  const tokens = await refreshTokens(await readRefreshToken());
  if (!tokens) {
    const res = NextResponse.json(
      { error: { code: "UNAUTHENTICATED" } },
      { status: 401 },
    );
    clearSessionCookies(res);
    return res;
  }
  const res = NextResponse.json({ ok: true });
  setSessionCookies(res, tokens);
  return res;
}
