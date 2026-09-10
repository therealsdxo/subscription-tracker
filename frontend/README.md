# HealthX — Frontend

Internal operations UI for HealthX staff. Next.js (App Router) + TypeScript +
Tailwind v4, talking to the FastAPI backend through a **same-origin server
proxy**. Design reference: `../progress/tech_doc.md` §14.1, `../progress/questionnaire.md`.

## Requirements

- Node 20+ and **pnpm 9** (`corepack enable`)
- The backend running locally (`../backend`, on `:8000`)

## Setup

```bash
pnpm install
cp .env.example .env        # HEALTHX_API_URL points at the backend
pnpm dev                    # http://localhost:3000
```

Log in with the backend's seed admin (`HEALTHX_SEED_ADMIN_*`).

## Scripts

| Script                         |                                                                       |
| ------------------------------ | --------------------------------------------------------------------- |
| `pnpm dev` / `build` / `start` | Next.js                                                               |
| `pnpm lint` / `typecheck`      | ESLint / `tsc --noEmit`                                               |
| `pnpm test` / `test:watch`     | Vitest + React Testing Library                                        |
| `pnpm format`                  | Prettier                                                              |
| `pnpm gen:api`                 | regenerate `lib/api/schema.d.ts` from `$HEALTHX_API_URL/openapi.json` |

## Auth model — no tokens in the browser

The FastAPI API is bearer-token (short access + rotating refresh). This app
never exposes a token or the backend URL to client JS:

- `app/api/auth/{login,logout,refresh}/route.ts` — Route Handlers that call the
  API and set the tokens as **httpOnly, Secure, SameSite=Lax cookies**
  (`hx_access`, `hx_refresh`).
- `app/api/v1/[...path]/route.ts` — a catch-all **proxy**. Every browser call
  goes to `/api/v1/*`; the proxy attaches the access token from the cookie,
  and on a `401` transparently refreshes (rotating the refresh cookie) and
  retries once. If refresh fails it clears the cookies and returns `401`.
- `middleware.ts` — redirects unauthenticated page requests to
  `/login?next=…`; sends a logged-in user away from `/login`.
- The typed client (`lib/api/client.ts`, `openapi-fetch`) is pointed at the
  same origin, so it just works inside TanStack Query hooks
  (`lib/api/hooks/*`).

## Design tokens

All colours, radii and the font are semantic CSS variables in
`app/globals.css` (`@theme`), consumed as Tailwind utilities
(`bg-surface`, `text-text-muted`, `border-border`, `rounded-[var(--radius)]`, …).
White / off-white / black / slate, one near-black accent, ~5px radii, 1px
hairlines. No gradients, glass, oversized cards, or decorative charts.

## Adding a list screen

Follow `app/(app)/customers/page.tsx`:

1. Add a typed hook in `lib/api/hooks/<resource>.ts` using
   `api.GET("/api/v1/<resource>", { params: { query } })` and
   `components["schemas"]["Page_<X>_"]`.
2. A client page with a search `<Input>`, filters, `<Table>` from
   `components/ui/table`, and `<Pagination>`.
3. Row `onClick` → the detail route.

## Layout

```
app/
  layout.tsx            root — fonts, <QueryProvider>
  (auth)/login/         the only unauthenticated screen
  (app)/                <AppShell> layout (sidebar + topbar + logout)
    dashboard/          GET /dashboard/summary — 5 stat tiles
    customers/          GET /customers — the reference list screen
    <others>/           placeholders
  api/auth/*            cookie-setting route handlers
  api/v1/[...path]/     the authenticated proxy
components/ui/          Button, Input, Field, Table, Pagination, StatusPill, …
components/app-shell/   Sidebar + Topbar
lib/                    cn, constants, env (server-only), api client + hooks
middleware.ts           route guard
test/                   Vitest
```

## Deployment

Hosting infra (Amplify / S3+CloudFront, or ECS + an ALB rule) is a follow-up —
see `../infra/`. The app needs `HEALTHX_API_URL` (server-only) and
`HEALTHX_COOKIE_SECURE=true` in production.
