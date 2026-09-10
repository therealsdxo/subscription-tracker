import { NextResponse } from "next/server";

import { clearSessionCookies } from "@/lib/server/auth";

export async function POST() {
  const res = new NextResponse(null, { status: 204 });
  clearSessionCookies(res);
  return res;
}
