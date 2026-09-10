/**
 * Server-only configuration. Importing this from a Client Component is a build
 * error, which is the point — the API URL and cookies never reach the browser.
 */
import "server-only";

export { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/constants";

export const env = {
  apiUrl: process.env.HEALTHX_API_URL ?? "http://localhost:8000",
  cookieSecure: process.env.HEALTHX_COOKIE_SECURE !== "false",
};
