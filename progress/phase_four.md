# Goals

1. You're the senior backend engineer continuing HealthX. Work strictly from
   `project.md`, `progress/questionnaire.md`, `progress/tech_doc.md`, and the code
   already on `main` (Milestones 1–2). Follow the established patterns: routers →
   services (transactional, own every invariant) → repositories → models;
   Pydantic schemas per resource; `audit_service.record()` for sensitive actions;
   `code_service.next_code()` for human codes; ADMIN/STAFF guards from
   `app.core.deps`; explicit enum create/drop in migrations; up/down-clean.

2. Deliver **Milestone 3 — Subscriptions** (`tech_doc.md` §16). This is the core
   of the system. **Deliveries and payments are not in this phase** (M4 / M5) —
   but nothing here may block them, and `meals_consumed` must be a real,
   mutable column that deliveries will decrement later.

3. First, close the Milestone 2 stubs:
   - Replace `package_service.is_package_referenced()` with a real `EXISTS`
     against `subscriptions.package_id`. Add a test: a package used by any
     subscription cannot be `DELETE`d (409 `PACKAGE_IN_USE`) and can only be
     deactivated (BR-6).
   - Block assigning an `INACTIVE` package to a new subscription (BR-7).
   - Add a subscriptions summary to `CustomerDetail` (`tech_doc.md` §8): current
     subscription (if any) + count of past subscriptions.

4. Enums (`app/models/enums.py`):
   - `SubscriptionStatus`: `PENDING`, `ACTIVE`, `PAUSED`, `COMPLETED`, `EXPIRED`,
     `CANCELLED` (`tech_doc.md` §4.5).
   - `DeliveryFrequency`: `DAILY`, `SPECIFIC_WEEKDAYS`, `CUSTOM` (Q6.1).
   - `TimeSlot`: `MORNING`, `LUNCH`, `EVENING`, `CUSTOM` (Q6.11).
   - `SubscriptionEventType`: `CREATED`, `ACTIVATED`, `PAUSED`, `RESUMED`,
     `EXTENDED`, `COMPLETED`, `EXPIRED`, `CANCELLED`, `RENEWED`.

5. Migration `0003_subscriptions` (`tech_doc.md` §3.3):
   - `subscription_code_seq` (+ register it in `app/models/sequences.py`).
   - `subscriptions`:
     - `id`, `subscription_code` (unique), `customer_id` FK, `package_id` FK
       (reference only), `subscription_number` (int, per-customer ordinal),
       `status` enum,
     - `start_date`, `original_end_date`, `expected_end_date`, `actual_end_date`
       (nullable),
     - snapshot columns: `snapshot_package_name`, `snapshot_package_description`
       (nullable), `snapshot_number_of_meals`, `snapshot_validity_days`,
       `snapshot_base_price`, `snapshot_tax_amount`, `snapshot_final_price`,
     - `meals_allocated`, `meals_consumed` (default 0), `meals_adjustment`
       (default 0), and `meals_remaining` as a **generated column**
       (`meals_allocated + meals_adjustment - meals_consumed`),
     - `delivery_frequency` enum, `delivery_weekdays` `int[]` (nullable; required
       when `SPECIFIC_WEEKDAYS`), `custom_schedule` `jsonb` (nullable; required
       when `CUSTOM`), `meals_per_delivery` (int, ≥ 1, default 1),
     - `delivery_time_slot` enum, `delivery_time_slot_note` (nullable),
     - `delivery_address_id` FK `customer_addresses` (nullable on delete
       SET NULL), `snapshot_delivery_address` `jsonb`,
     - `snapshot_dietary_preference` enum (nullable), `subscription_notes`
       (nullable),
     - `previous_subscription_id` FK self (nullable),
     - `cancelled_at` / `cancelled_by` / `cancellation_reason`,
     - timestamps + `created_by` / `updated_by`.
   - **Partial unique index**: at most one row per `customer_id` with
     `status = 'ACTIVE'`.
   - Check constraints: `meals_per_delivery >= 1`, `snapshot_number_of_meals >= 1`,
     `meals_consumed >= 0`.
   - Indexes: `(status, expected_end_date)`, `(customer_id, status)`.
   - `subscription_events`: `id`, `subscription_id` FK, `event_type` enum,
     `reason` (nullable), `effective_date`, `pause_start` / `pause_end` /
     `paused_days` (nullable), `old_expected_end_date` / `new_expected_end_date`
     (nullable), `performed_by`, `performed_at`. Immutable — no update path.
   - `meal_adjustments`: `id`, `subscription_id` FK, `quantity` (signed,
     non-zero), `reason` (not null), `performed_by`, `performed_at`.

6. Business rules to enforce in the service layer:
   - **Snapshot on create** (BR-8): copy package name/description/meals/
     validity_days/base_price/tax_amount/final_price; snapshot the chosen
     delivery address (jsonb) and the customer's dietary preference.
     `meals_allocated = snapshot_number_of_meals` (BR-9).
   - **Expiry math** (BR-10, Q0.5, Q4.3): `original_end_date = start_date +
     snapshot_validity_days` (calendar days). `expected_end_date` starts equal to
     it and is only moved by pause-resume and admin extension. Tuesdays / holidays
     do **not** extend it.
   - `start_date` may be back-dated / today / future-dated; a Tuesday start is
     allowed (BR-11, BR-12). Always record who created/changed the subscription.
   - **One ACTIVE per customer** (BR-13): if the customer already has an `ACTIVE`
     subscription, the new one is `PENDING`. A future `start_date` with no current
     ACTIVE also yields `PENDING` until the start date. Meal balances are never
     combined.
   - `subscription_number` = ordinal among that customer's subscriptions, first
     = 1 (BR-14). Store it, but reconcile with `count()` on read.
   - **COMPLETED** when `meals_remaining == 0` (BR-19) — reachable in this phase
     via a negative meal adjustment. No further state changes except renewal.
   - **EXPIRED** when `today > expected_end_date` for an `ACTIVE`/`PAUSED`
     subscription (BR-20); remaining meals forfeited.
   - **Pause / resume** (BR-22): ADMIN or STAFF, reason required. On resume,
     `expected_end_date += paused_days`. Writes `PAUSED` / `RESUMED` events.
   - **Extend** (BR-21): ADMIN only, mandatory reason, by N days or to a date.
     Records old/new expiry. Extending an `EXPIRED` subscription with a future
     new date returns it to `ACTIVE`.
   - **Cancel** (BR-23): ADMIN only, reason required. No automatic refund.
   - **Meal adjustment** (BR-18): ADMIN only, non-zero quantity + reason, audited;
     moves `meals_adjustment`; may trigger `COMPLETED` at zero.
   - **Hybrid status recompute** (BR-24): `status` is stored, but every read and
     every state-changing operation first re-evaluates expiry / completion. Add a
     `workers/expiry_job.py` function (callable from a script) that (a) activates
     `PENDING` subscriptions whose `start_date <= today` and whose customer has no
     `ACTIVE` subscription, and (b) expires overdue `ACTIVE`/`PAUSED` ones. Wire
     it as `python -m scripts.run_expiry_job`; scheduling is infra (M6).
   - **Renewal** (BR-32…BR-35): `POST /subscriptions/{id}/renew` creates a new
     subscription linked via `previous_subscription_id`, may use **any ACTIVE
     package** (not necessarily the same one), starts `PENDING` if the customer
     still has an ACTIVE subscription (else `ACTIVE` / future `PENDING`). Unused
     meals do **not** carry over.

7. Endpoints (`tech_doc.md` §8):
   - `GET /subscriptions` — filters `status`, `customer_id`, `expiring=true`
     (within `expiry_days_threshold` days **or** ≤ `expiry_meals_threshold` meals,
     from `settings`); paginated.
   - `POST /subscriptions` — create (snapshot happens here). STAFF.
   - `GET /subscriptions/{id}` — detail incl. recomputed status, meal counts,
     snapshot, and its `events`.
   - `PATCH /subscriptions/{id}` — edit only `subscription_notes`,
     `delivery_frequency` (+weekdays/custom_schedule), `meals_per_delivery`,
     `delivery_time_slot(_note)`, `delivery_address_id` (re-snapshots the
     address). STAFF. Never edits dates, status, or snapshot money/meal fields.
   - `POST /subscriptions/{id}/pause` · `/resume` — STAFF, `{reason}`.
   - `POST /subscriptions/{id}/extend` — ADMIN, `{days | new_end_date, reason}`.
   - `POST /subscriptions/{id}/cancel` — ADMIN, `{reason}`.
   - `POST /subscriptions/{id}/renew` — STAFF, `{package_id, start_date, …}`.
   - `POST /subscriptions/{id}/meal-adjustments` — ADMIN, `{quantity, reason}`.
   - `GET /subscriptions/{id}/events` — the lifecycle log.
   - Guard rails: can't pause a non-ACTIVE sub; can't resume a non-PAUSED sub;
     can't extend/cancel a `COMPLETED`/`CANCELLED` sub; can't adjust meals on a
     `CANCELLED` sub.
   - Payment fields (`payment_status`, `outstanding_amount`) are **out of scope**
     for M3 — the subscription output carries `snapshot_final_price` only; the
     derived payment view lands in M5.

8. Models: register `Subscription`, `SubscriptionEvent`, `MealAdjustment` in
   `app/models/__init__.py`. Relationship stubs for deliveries/payments are **not**
   added yet.

9. Tests (`pytest`) — priority order from Q1.7:
   - Subscription creation: snapshot correctness (edit the package afterwards,
     confirm the subscription is unchanged — BR-5); `meals_allocated`; code
     `SUB-000001`; `subscription_number` increments per customer.
   - One-ACTIVE rule: second subscription for the same customer is `PENDING`;
     PENDING activates via the expiry job when the first ends.
   - Expiry math: `original_end_date = start + validity_days`; the worked example
     (25-meal / 50-day, `start_date = 2026-09-01` → `2026-10-21`); Tuesday /
     holiday do not extend; extend moves the date and re-activates an EXPIRED sub;
     pause→resume adds exactly the paused days.
   - Meal balance: negative adjustment reduces `meals_remaining`; hitting 0 →
     `COMPLETED`; positive goodwill adjustment; `meals_adjustment` audited.
   - Guard rails + RBAC (STAFF can't extend/cancel/adjust; ADMIN can).
   - Renewal: creates a linked `PENDING` subscription; different package allowed;
     no meal carryover; `previous_subscription_id` set.
   - `is_package_referenced()` now true → package delete blocked.
   - `run_expiry_job`: activates due PENDING, expires overdue.

10. Deliverables check:
    - `alembic upgrade head` → `downgrade base` → re-`upgrade` clean on a fresh DB.
    - `make check` (ruff + mypy strict + pytest) green.
    - New endpoints in `/docs`; a manual run: create package → create customer →
      create subscription (snapshot verified) → adjust meals → pause/resume →
      extend → renew.
    - Update `backend/README.md` (endpoints + the expiry job) and record open
      items at the end of this file.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Open questions / deferred

_(fill in during the work)_
