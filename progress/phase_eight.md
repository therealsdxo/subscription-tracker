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

# Open questions / deferred

_(fill in during the work)_
