# Goals

1. You're a senior frontend engineer with 15–20 years building production web
   apps. Work strictly from `project.md`, `progress/questionnaire.md`,
   `progress/tech_doc.md`, and the **running backend** on `main` (the FastAPI API,
   Milestones 1–6). The API contract is authoritative — read it from
   `http://localhost:8000/openapi.json` (or `/docs`).

2. Scaffold the **frontend** only — a runnable Next.js skeleton with the
   foundations and two reference screens wired end to end. This is the frontend
   equivalent of `progress/phase_two.md`: **no attempt to build all 17 screens**
   (`tech_doc.md` §9.2). Prove the stack with Login + Dashboard + Customers list,
   and leave a clear pattern for the rest.

3. Create `frontend/` at the repo root. Stack (`questionnaire.md` §1.3,
   `tech_doc.md` §2.2):
   - **Next.js 15** (App Router, TypeScript **strict**), **React 19**
   - **Tailwind CSS v4**
   - **pnpm** as the package manager
   - **TanStack Query** for server state; **react-hook-form** + **zod** for forms
   - **Radix UI primitives** for dialog / dropdown / select / toast — styled by
     us, not a pre-built component kit (keep control of the aesthetic)
   - **openapi-typescript** + **openapi-fetch** for a fully typed API client
     generated from the backend's OpenAPI schema
   - ESLint (next config) + Prettier; Vitest + React Testing Library

4. **Design language** (`questionnaire.md` §1.3, §10.6, `tech_doc.md` §14.1) —
   this is a hard constraint, get it right in the scaffold:
   - Palette: white, off-white, black, slate. Define semantic tokens
     (`--bg`, `--surface`, `--border`, `--text`, `--text-muted`, `--accent`) in
     one place; wire them into the Tailwind theme. One restrained accent (a
     dark slate or near-black), used sparingly.
   - Very restrained rounded corners (≈ `4–6px` max). Thin `1px` borders.
     Dense, legible tables. System font stack or one neutral sans (Inter).
   - **No** gradients, glassmorphism, purple/blue "AI" palettes, oversized
     cards, heavy shadows, decorative charts, or gratuitous animation.
   - Minimal, professional, operational. Desktop-first, responsive down to
     tablet/mobile (`questionnaire.md` §10.4); no offline mode (§10.5).

5. **Auth** (`tech_doc.md` §5, internal staff only, email + password):
   - The API is bearer-token (short access + rotating refresh). **Do not put
     tokens in `localStorage`.** Use a thin server layer: Next.js Route Handlers
     (`app/api/auth/*`) call the FastAPI, and the tokens live in **httpOnly,
     Secure, SameSite=Lax cookies** set by the Next server.
   - All API calls from the browser go through a **server proxy**
     (`app/api/[...path]/route.ts` or a server action / RSC fetch wrapper) that
     attaches the access token from the cookie and, on `401`, transparently
     refreshes (rotating the refresh cookie) and retries once. On refresh
     failure → clear cookies, redirect to `/login`.
   - `middleware.ts` guards every route except `/login` and static assets;
     unauthenticated → redirect to `/login?next=…`.
   - Surface the login rate-limit `429` (`Retry-After`) as a friendly message.

6. **App shell & routing**:
   - `(auth)/login` — email + password form (react-hook-form + zod), inline
     errors, disabled-while-submitting, rate-limit message.
   - `(app)/` layout — a left sidebar (Dashboard, Customers, Packages,
     Subscriptions, Deliveries, Payments, Settings — most linking to
     placeholder pages) + a top bar with the app name, the current user's name,
     and a logout button. Sidebar collapses to a drawer on small screens.
   - Placeholder route for each nav item so links don't 404; a shared
     `<PageHeader>` and empty-state component.

7. **Reference screens** (wired to the real API):
   - `(app)/dashboard` — `GET /api/v1/dashboard/summary`. Five plain stat tiles
     (active subscriptions, today's meals, delivered today, expiring soon,
     outstanding dues) — small, bordered, no charts. Loading + error states.
   - `(app)/customers` — `GET /api/v1/customers` with the search box
     (`?q=`/`?phone=`/`?code=`), an `is_active` filter, a dense table
     (code, name, phone, status), and pagination (`page`/`page_size`, the
     `{items,total,page,page_size}` envelope). Row → `/customers/[id]`
     placeholder. This is the template every list screen will follow.

8. **API client & types**:
   - `pnpm gen:api` script → `openapi-typescript http://localhost:8000/openapi.json
     -o src/lib/api/schema.d.ts` (commit the output).
   - A typed `apiClient` wrapper (`openapi-fetch`) pointed at the **same-origin
     proxy** (`/api/v1`), used inside TanStack Query hooks
     (`src/lib/api/hooks/*`). One `useAuth()` context for the current user
     (fetched from `GET /auth/me`).
   - Map the API's `{ error: { code, message }, warnings: [] }` envelope to a
     typed error; a small toast for mutation errors/warnings.

9. **Config & env**:
   - `HEALTHX_API_URL` (server-only, e.g. `http://localhost:8000`) for the proxy;
     `.env.example`. No API URL or token ever exposed to the client bundle.
   - `next.config.ts`, `tsconfig.json` (strict, path alias `@/*`),
     `tailwind` v4 config, `.prettierrc`, ESLint config.

10. **Testing**:
    - Vitest + RTL: the login form (validation, submit, error), the dashboard
      tiles (renders values from a mocked response), the customers table
      (renders rows, pagination controls, search updates the query). Mock the
      proxy with MSW or a fetch stub.
    - One Playwright smoke test is optional this phase (login → dashboard) —
      note it if skipped.

11. **CI** — add `.github/workflows/frontend-ci.yml`: pnpm install (frozen
    lockfile) → `lint` → `typecheck` (`tsc --noEmit`) → `test` → `build`.
    Trigger on `frontend/**`.

12. **Deliverables check**:
    - `pnpm dev` runs; `/login` → authenticate against the local API → land on
      `/dashboard` with real numbers → `/customers` lists + searches + paginates
      → logout returns to `/login`.
    - `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all green.
    - Tokens are httpOnly cookies only (verify in devtools: nothing in
      `localStorage`/`sessionStorage`, no token in any client-visible response).
    - `frontend/README.md` — setup, the auth model, the design tokens, how to
      add a new list screen, and `pnpm gen:api`.
    - Update the root `README.md` (frontend is now started) and record open
      items at the end of this file.
    - **Frontend hosting infra** (Amplify / S3+CloudFront, or ECS + an ALB rule)
      is **out of scope** — note it as a follow-up alongside `infra/`.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Status — frontend scaffold complete (2026-09-10)

Delivered on branch `feat-frontend-scaffold`, in `frontend/`.

- **Stack**: Next.js 15 (App Router, TS strict), React 19, **Tailwind v4**,
  **pnpm 9**. TanStack Query, react-hook-form + **zod 4**
  (`z.email`, `<form noValidate>`), Radix `label`/`slot`/`dialog`/`dropdown`,
  `openapi-fetch` + `openapi-typescript` (`lib/api/schema.d.ts` generated from
  the backend OpenAPI — 47 paths), Vitest + RTL, ESLint + Prettier.
- **Design tokens** (`app/globals.css` `@theme`): `--color-bg` off-white,
  `--color-surface` white, near-black text + one dark-slate accent, `--radius`
  5px, 1px `--color-border`. Consumed as Tailwind utilities. No gradients /
  glass / oversized cards / charts.
- **Auth without browser tokens**:
  - `app/api/auth/{login,logout,refresh}/route.ts` set/clear **httpOnly Secure
    SameSite=Lax** cookies (`hx_access`, `hx_refresh`); login body is `{ok:true}`.
  - `app/api/v1/[...path]/route.ts` — catch-all proxy; attaches the access
    token, refreshes + retries once on 401, clears cookies + 401 on failure.
  - `middleware.ts` — redirect to `/login?next=…` when no `hx_refresh`; bounce
    a logged-in user off `/login`.
  - Verified live: cookies are httpOnly, nothing in `localStorage`, no token in
    any client-visible response.
- **App shell** (`components/app-shell/`): sidebar (7 nav items) + topbar with
  the current user + logout; collapses to a drawer on mobile. Placeholder page
  for every nav item so links don't 404.
- **Reference screens** wired to the real API:
  - `(app)/dashboard` — `GET /api/v1/dashboard/summary`, five plain stat tiles.
  - `(app)/customers` — `GET /api/v1/customers` with search, `is_active`
    filter, dense `<Table>`, `<Pagination>`; row → `/customers/[id]`.
- **UI kit** (`components/ui/`): Button, Input, Field, Table, Pagination,
  Spinner, PageHeader, EmptyState, ErrorState, StatusPill, Placeholder.
- **Tests** (`test/`, 7): login (validation / redirect / 429 message),
  dashboard tiles (values + error state), customers table (rows + pagination +
  search → query).
- **CI**: `.github/workflows/frontend-ci.yml` — pnpm install (frozen) → lint →
  build → typecheck → test; triggers on `frontend/**`.
- **Backend fix carried in this branch**: `Settings.cors_origins` was
  `list[str]` and pydantic-settings JSON-parsed the env value, crashing on a
  plain comma-separated `HEALTHX_CORS_ORIGINS`. Added `NoDecode`. (The frontend
  doesn't use CORS — it proxies same-origin — but the M6 Terraform passes a
  plain string, so this would have broken the deploy.)

Verified locally: `pnpm lint` / `typecheck` / `test` / `build` green; live run
against the backend — login → httpOnly cookies → dashboard numbers → customer
search → logout → middleware redirect.

# Open questions / deferred

- **The other ~13 screens** (`tech_doc.md` §9.2) — packages, subscriptions,
  deliveries, payments, settings, all the detail/create forms. Each follows the
  Customers list / login form patterns.
- **CSV export/import UI** — download buttons and the import wizard are not
  built; the API endpoints exist.
- **Frontend hosting infra** — Amplify Hosting or S3+CloudFront (or ECS + an
  ALB path rule sharing the API's domain). Not in `infra/` yet.
- **Toasts for mutation errors/warnings** — Radix Toast is installed and the
  error-envelope mapper exists (`errorMessage`), but no global toaster is
  mounted (no mutations in the scaffold yet).
- **Refresh-token rotation & the proxy**: the proxy retries once on 401 and
  writes rotated cookies onto that response. A burst of parallel requests that
  all 401 at once will each try to refresh; the last write wins. Fine at v1
  concurrency; a single-flight refresh lock is the tidy fix.
- **Playwright E2E** — skipped this phase; Vitest covers the components.
- **`next-env.d.ts`** is committed (without the `.next/types/routes.d.ts`
  triple-slash ref) so CI can typecheck before the build; `next build`
  re-adds that line locally — a harmless 1-line diff.
- **pnpm version**: pinned to `pnpm@9.15.4` (`packageManager`). pnpm 12 (what
  corepack pulls as "latest") hard-errors on any ignored dependency build
  script even with an allowlist.
