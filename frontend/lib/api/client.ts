import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

/**
 * Same-origin client. Every call goes to `/api/v1/*`, which the Next server
 * proxies to the FastAPI backend after attaching the access token from an
 * httpOnly cookie. The browser never sees a token or the backend URL.
 */
export const api = createClient<paths>({ baseUrl: "" });

export type ApiError = {
  error: { code: string; message: string; details?: unknown[] };
  warnings?: { code: string; message: string }[];
};

export function errorMessage(body: unknown, fallback = "Something went wrong"): string {
  if (
    body &&
    typeof body === "object" &&
    "error" in body &&
    body.error &&
    typeof body.error === "object" &&
    "message" in body.error &&
    typeof body.error.message === "string"
  ) {
    return body.error.message;
  }
  return fallback;
}
