# Goals

1. You're the senior backend engineer completing HealthX v1. Work strictly from
   `project.md`, `progress/questionnaire.md`, `progress/tech_doc.md`, and the code
   on `main` (Milestones 1–5). Keep the established patterns: routers → services
   (transactional) → repositories → models; Pydantic schemas per resource;
   `audit_service.record()` for sensitive actions; ADMIN/STAFF guards; explicit
   enum create/drop in migrations; `alembic upgrade`/`downgrade` clean.

2. Deliver **Milestone 6 — Dashboard, reporting & deploy** (`tech_doc.md` §16,
   §9, §10, §11). This closes out the backend for v1. There is no frontend yet,
   so frontend hosting infra is out of scope — the deploy artifacts cover the
   API, the database, and the scheduled job only.

3. **Dashboard summary** — `GET /dashboard/summary` (STAFF), `tech_doc.md` §9.4:
   - `active_subscriptions` — count `status = ACTIVE`
   - `todays_meals_planned` — Σ `meal_quantity` of today's non-terminal deliveries
   - `delivered_today` — count today's `DELIVERED`
   - `expiring_soon` — subscriptions where
     `expected_end_date - today ≤ expiry_days_threshold` **OR**
     `meals_remaining ≤ expiry_meals_threshold` (thresholds from `settings`),
     `status IN (ACTIVE, PAUSED)`
   - `outstanding_dues_total` — Σ `outstanding_amount` over non-terminal
     subscriptions (reuse `payment_repo.outstanding_expr` / the payment summary
     maths)
   - Keep it a single service call with a handful of aggregate queries — no
     per-row Python loops.

4. **Monitoring lists** (`tech_doc.md` §9.2) — most already exist:
   `GET /subscriptions?status=` / `?expiring=true` / `?dues=true`,
   `GET /deliveries?date=`, `GET /customers`. Confirm each is present and
   paginated; add nothing new unless a listed screen has no endpoint.

5. **CSV export** (`tech_doc.md` §9.3) — `GET /exports/{resource}.csv` (STAFF),
   streamed `text/csv` with a `Content-Disposition` filename:
   - `customers.csv` — code, name, phone, email, dietary, allergies, is_active,
     created_at, primary address fields
   - `subscriptions.csv` — code, customer code/name, status, package snapshot,
     dates, meals allocated/consumed/remaining, payment_status, outstanding
   - `payments.csv` — id, subscription code, customer code, amount, method,
     reference, payment_date, recorded_by
   - `deliveries.csv` — accepts `?date=` (defaults to today); date, slot, status,
     customer, area, meal_quantity, meals_deducted
   - Reuse the existing repos/search; stream so a large export doesn't buffer the
     whole result set in memory (use a generator + `StreamingResponse`).
   - UTF-8, `\r\n`, ISO dates, plain-decimal amounts.

6. **CSV customer import** (`tech_doc.md` §10.7, Q10.7) — `POST /imports/customers`
   (**ADMIN**), multipart file upload, `mode` query param `validate` (default) or
   `commit`:
   - Parse + validate every row against the same rules as `POST /customers`
     (required name/phone/address, phone/email uniqueness incl. within the file,
     enum values, structured address). Return
     `{ total, valid, invalid, committed, errors: [{ row, field, message }] }`.
   - `mode=validate` never writes. `mode=commit` writes **all valid rows in one
     transaction** (or aborts if any row is invalid — pick and document one:
     recommended **all-or-nothing when `invalid > 0`**, i.e. reject the commit
     and report the errors).
   - Optional columns may seed a *current* subscription per customer
     (`package_code`, `start_date`, `delivery_frequency`, `delivery_weekdays`,
     `meals_per_delivery`, `time_slot`) — validate the package is `ACTIVE`;
     reuse `subscription_service`. If subscription columns are absent, just the
     customer + address are created.
   - Document the template columns in `backend/README.md` and ship an example
     `backend/docs/customers_import_template.csv`.
   - This is a **stateless validate/commit**, not the two-phase job model in
     `tech_doc.md` §10 — simpler and adequate for one admin doing occasional
     imports. Note the deviation in the open-questions section.
   - `audit CUSTOMERS_IMPORTED` with the counts.

7. **Auth rate-limiting** (production readiness, `tech_doc.md` §5.1 — deferred
   from M1):
   - A lightweight in-process limiter on `POST /auth/login`: per-IP
     (e.g. 10 attempts / 5 min) and a per-account backoff after N consecutive
     failures. 429 with a `Retry-After` header.
   - In-process is fine for v1 (single task); note that a multi-task deployment
     needs a shared store (Redis) — flag it.

8. **Ops scripts**:
   - `scripts/generate_deliveries.py` — generate the day's deliveries for a given
     date (default: tomorrow, in `Asia/Kolkata`), reusing `delivery_service`.
   - Keep `scripts/run_expiry_job.py` (M3) as-is.

9. **Containerisation**:
   - `backend/Dockerfile` — multi-stage, `python:3.13-slim`, `uv sync --no-dev`,
     non-root user, `CMD` runs `uvicorn app.main:app` on `$PORT`.
   - `backend/.dockerignore`.
   - A `docker build` must succeed (author it correctly even if Docker isn't
     available in this environment — verify by inspection + `uv` parity).

10. **AWS infrastructure** — `infra/` Terraform, **authored and
    `terraform validate` / `plan`-clean, not applied** (`tech_doc.md` §11):
    - `infra/README.md` — what it provisions, the `terraform apply` runbook,
      and how the app's env vars / secrets map in.
    - Region `ap-south-1`. Modules / files:
      - **network** — VPC, 2 public + 2 private subnets, IGW, NAT (single for
        cost), route tables, security groups (ALB→ECS, ECS→RDS).
      - **database** — RDS PostgreSQL 16, private, `db.t4g.micro` (v1),
        automated backups (7–14 day retention) + PITR, deletion protection,
        Multi-AZ as a documented toggle (default off for v1).
      - **registry** — ECR repo for the API image, lifecycle policy.
      - **service** — ECS cluster (Fargate), task definition (API container +
        the migration step as a one-off / init), ALB with HTTPS
        (ACM cert, HTTP→HTTPS redirect), target group health check on
        `/api/v1/health`, autoscaling target (1–4 tasks).
      - **secrets** — Secrets Manager entries for `HEALTHX_DATABASE_URL`,
        `HEALTHX_JWT_SECRET`; task role reads them.
      - **scheduler** — EventBridge Scheduler rule → a one-off ECS task running
        `python -m scripts.run_expiry_job` daily (early morning IST); a second
        rule for `scripts.generate_deliveries` if the outlet wants
        pre-generation.
      - **observability** — CloudWatch log group; alarms on ALB 5xx rate, target
        latency p95, RDS CPU / free storage / connection count; an SNS topic for
        alarm notifications.
    - Variables in `infra/variables.tf` with sane v1 defaults; `terraform.tfvars.example`.
    - Do **not** commit any real account id, secret, or `.tfstate`; `.gitignore`
      the state and `.terraform/`.
    - Frontend hosting (Amplify / S3+CloudFront) is **out of scope** — no
      frontend exists. Note it as a follow-up.

11. **CI** — extend `.github/workflows/backend-ci.yml`:
    - Add a `docker build` of `backend/Dockerfile` (build only, no push) so the
      image can't silently break.
    - Optionally add `terraform fmt -check` + `terraform validate` for `infra/`
      (no AWS creds needed for `validate` with a stubbed backend).

12. **Tests** (`pytest`):
    - Dashboard: seed a mix of subscriptions / deliveries / payments and assert
      every summary field; empty-system returns all zeros.
    - CSV export: each endpoint returns `text/csv`, the right header row, one
      data row per record, and honours filters (`deliveries.csv?date=`).
    - CSV import: a good file `mode=validate` reports `valid == total`,
      `committed == false`, writes nothing; `mode=commit` creates the customers +
      addresses (+ subscription when columns present); a file with a duplicate
      phone (in-file and vs. DB) reports the row errors and, on `mode=commit`
      with `invalid > 0`, writes nothing.
    - Rate limiting: the (N+1)th rapid bad login returns 429 with `Retry-After`;
      a good login within the window still succeeds until the IP cap; the
      counter is per-IP.
    - `scripts.generate_deliveries` for an explicit date creates the expected
      rows (reuse the M4 helpers).

13. **Deliverables check**:
    - `alembic upgrade head` → `downgrade base` → re-`upgrade` clean (no schema
      change is expected this milestone unless import needs one — avoid it).
    - `make check` (ruff + mypy strict + pytest) green.
    - `terraform init -backend=false && terraform validate` passes in `infra/`.
    - New endpoints in `/docs`; a manual run: `GET /dashboard/summary` →
      export each CSV → import a small customers file (`validate` then `commit`).
    - Update `backend/README.md` (dashboard, exports, import template, rate
      limiting, Docker) and write `infra/README.md`. Record open items at the
      end of this file.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Open questions / deferred

_(fill in during the work)_
