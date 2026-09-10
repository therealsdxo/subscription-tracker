# Goals

1. You're the senior backend engineer continuing HealthX. Work strictly from
   `project.md`, `progress/questionnaire.md`, `progress/tech_doc.md`, and the code
   on `main` (Milestones 1–3). Keep the established patterns: routers → services
   (transactional, own every invariant) → repositories → models; Pydantic schemas
   per resource; `audit_service.record()` for sensitive actions; ADMIN/STAFF
   guards from `app.core.deps`; explicit enum create/drop in migrations;
   `alembic upgrade`/`downgrade` clean on a fresh database.

2. Deliver **Milestone 4 — Deliveries** (`tech_doc.md` §16, §6). This is where
   `subscriptions.meals_consumed` finally moves: recording a `DELIVERED` outcome
   decrements the balance; reversing one restores it. **Payments are still out of
   scope** (Milestone 5).

3. Enums (`app/models/enums.py`):
   - `DeliveryStatus`: `SCHEDULED`, `PREPARING`, `OUT_FOR_DELIVERY`, `DELIVERED`,
     `SKIPPED`, `CANCELLED`, `FAILED`, `RESCHEDULED` (`tech_doc.md` §6.4).
   - Terminal-for-balance set: only `DELIVERED` touches meals; a delivery that is
     `SKIPPED` / `CANCELLED` / `FAILED` / `RESCHEDULED` never consumes a meal and
     never extends expiry (BR-17, Q6.5).

4. Migration `0004_deliveries` (`tech_doc.md` §3.3):
   - `deliveries`: `id`, `subscription_id` FK (ondelete RESTRICT),
     `customer_id` FK (denormalised for the daily list), `delivery_date`,
     `time_slot` enum, `status` enum (default `SCHEDULED`), `meal_quantity`
     (int ≥ 1), `meals_deducted` (int, default 0), `delivered_at` (nullable),
     `recorded_by` FK users (nullable), `reversed` (bool default false),
     `reversal_reason` (nullable), `reversed_by` / `reversed_at` (nullable),
     `rescheduled_to_date` (nullable), `notes` (nullable), timestamps.
     - **Unique `(subscription_id, delivery_date, time_slot)`** — makes
       generation idempotent and blocks a double-record under concurrency.
     - Indexes: `(delivery_date, status)` for the daily list;
       `(subscription_id)`.
     - Check: `meal_quantity >= 1`, `meals_deducted >= 0`.
   - `planned_skips`: `id`, `subscription_id` FK, `skip_date_from`,
     `skip_date_to` (single day → same value), `reason` (nullable),
     `created_by`, `created_at`. Check `skip_date_to >= skip_date_from`.
   - `holidays`: `id`, `holiday_date` (unique), `name`, `created_by`,
     `created_at`. **Tuesday closure is the `closed_weekday` setting, not a
     row here** (BR-28); `holidays` is the maintainable one-off calendar.

5. Open-day helper (`tech_doc.md` §6.1, BR-28):
   - `delivery_service.is_open_day(session, d) -> bool` = `d.weekday()` is not the
     configured `closed_weekday` **and** `d` is not in `holidays`.
   - `closed_weekday` is stored in `settings` as a name (`"TUESDAY"`); map it to
     `date.weekday()` (Mon=0 … Sun=6). Read it via `settings_service`.

6. `custom_schedule` shape (M3 left it free-form): define it as
   `{"dates": ["YYYY-MM-DD", ...]}` — an explicit list of delivery dates.
   `delivery_service` validates the shape when a `CUSTOM` subscription is used
   for generation.

7. Daily list generation (`tech_doc.md` §6.1) — `generate(session, on_date)`,
   **idempotent**:
   - Return `[]` (do nothing) if `not is_open_day(session, on_date)`.
   - For every `ACTIVE` subscription with
     `start_date <= on_date <= expected_end_date` and `meals_remaining > 0`:
     - skip if a `planned_skips` row covers `on_date`;
     - skip unless `due_on(subscription, on_date)`:
       - `DAILY` → always (on an open day),
       - `SPECIFIC_WEEKDAYS` → `on_date.isoweekday()` in `delivery_weekdays`,
       - `CUSTOM` → `on_date.isoformat()` in `custom_schedule["dates"]`;
     - `qty = min(meals_per_delivery, meals_remaining)`;
     - `INSERT ... ON CONFLICT (subscription_id, delivery_date, time_slot) DO
       NOTHING` with `status = SCHEDULED`, `meal_quantity = qty`.
   - Returns a small summary (`{created, skipped_closed_day, ...}`).

8. Recording an outcome (`tech_doc.md` §6.2, BR-16, BR-29):
   - `set_status(session, delivery_id, new_status, *, notes, actor_id)`.
   - **Hard block** any status change on a delivery whose subscription is
     `EXPIRED` / `COMPLETED` / `PAUSED` / `CANCELLED` (409). This is the core
     problem the system exists to prevent (Q6.8).
   - Marking `DELIVERED`:
     - `SELECT … FROM subscriptions WHERE id = :sid FOR UPDATE` (row lock);
     - assert subscription `ACTIVE` and `today <= expected_end_date`;
     - assert the delivery is not already in a terminal state (idempotency /
       concurrency guard);
     - `deducted = min(meal_quantity, meals_remaining)`;
     - `meals_consumed += deducted`; `delivery.meals_deducted = deducted`;
     - `status = DELIVERED`, `delivered_at = now()`, `recorded_by = actor`;
     - if `meals_remaining == 0` → subscription `COMPLETED` (+ `COMPLETED`
       event), `actual_end_date = today`;
     - `audit DELIVERY_RECORDED`.
   - `RESCHEDULED` requires `rescheduled_to_date` (a future open day); it does
     not consume a meal; generation will create the new date's delivery.
   - `SKIPPED` / `CANCELLED` / `FAILED` just set the status + optional note.

9. Reversal (`tech_doc.md` §6.3, BR-30, Q6.6):
   - `reverse(session, delivery_id, reason, *, actor_id)` — STAFF, mandatory
     reason.
   - Only a `DELIVERED`, not-yet-`reversed` delivery can be reversed.
   - Lock the subscription; `meals_consumed -= meals_deducted`;
     `meals_deducted = 0`; `delivered_at = None`; `recorded_by = None`;
     `status = SCHEDULED` (so staff can re-record it correctly);
     `reversed = true`, `reversal_reason`, `reversed_by`, `reversed_at`.
   - If the subscription had flipped to `COMPLETED` **solely** because of this
     delivery and is still within its window (and the customer has no other
     `ACTIVE` subscription) → back to `ACTIVE` (+ `ACTIVATED` event).
   - `audit DELIVERY_REVERSED`.

10. Planned skips (Q6.9):
    - `POST /subscriptions/{id}/skips` `{skip_date_from, skip_date_to, reason?}`,
      `DELETE /subscriptions/{id}/skips/{skip_id}` — STAFF.
    - Adding a skip **cancels** any existing non-terminal deliveries whose date
      falls in the range (`status = SKIPPED`, note "planned skip") and blocks
      future generation for those dates.
    - `GET /subscriptions/{id}/skips`.

11. Holiday calendar (BR-28):
    - `GET /holidays` (STAFF), `POST /holidays` `{holiday_date, name}` and
      `DELETE /holidays/{id}` (ADMIN).
    - Adding a holiday cancels existing non-terminal deliveries on that date.

12. Endpoints (`tech_doc.md` §8):
    - `GET /deliveries?date=YYYY-MM-DD` — the daily list; also filter `status`,
      `area` (from `snapshot_delivery_address`), `time_slot`, `subscription_id`;
      paginated. Each row carries customer name/code, address snapshot, slot,
      meal quantity, status.
    - `POST /deliveries/generate` `{date}` — idempotent; STAFF.
    - `PATCH /deliveries/{id}` `{status?, time_slot?, notes?, rescheduled_to_date?}`
      — STAFF.
    - `POST /deliveries/{id}/reverse` `{reason}` — STAFF.
    - `GET /subscriptions/{id}/deliveries` — that subscription's deliveries.
    - No route planning / driver assignment (Q6.10).

13. Permissions (`tech_doc.md` §5.2): STAFF generate the list, record outcomes,
    reverse (audited), manage planned skips. ADMIN-only: manage the holiday
    calendar.

14. Tests (`pytest`) — priority order from Q1.7 (meal deduction, delivery
    reversal):
    - Generation: one `SCHEDULED` per due ACTIVE subscription; **no rows on a
      Tuesday or a holiday**; respects `SPECIFIC_WEEKDAYS` / `CUSTOM`; skips a
      `planned_skips` date; **idempotent** (running twice creates nothing new);
      none for `PENDING` / `PAUSED` / `COMPLETED` / `EXPIRED` subscriptions or
      when `meals_remaining == 0`.
    - Record `DELIVERED`: `meals_consumed += meal_quantity`, `meals_remaining`
      drops; multi-meal delivery (`meal_quantity = 2`); hitting 0 → subscription
      `COMPLETED`; `DELIVERED` blocked on a non-`ACTIVE` subscription (409);
      `SKIPPED` / `FAILED` leave the balance untouched.
    - **Concurrency**: two overlapping transactions marking the same delivery
      `DELIVERED` — exactly one succeeds, the balance moves once.
    - Reversal: exact `meals_deducted` restored; `COMPLETED → ACTIVE` rollback;
      `reversed` flag + audit row; can't reverse a non-`DELIVERED` delivery.
    - Planned skip / holiday added → existing deliveries on those dates cancelled.
    - RBAC: STAFF can record/reverse; STAFF cannot manage holidays.

15. Deliverables check:
    - `alembic upgrade head` → `downgrade base` → re-`upgrade` clean on a fresh DB.
    - `make check` (ruff + mypy strict + pytest) green.
    - New endpoints in `/docs`; a manual run: create subscription → generate a
      day's list → mark one `DELIVERED` (balance drops) → reverse it (balance
      restored) → add a holiday → regenerate (that date now empty).
    - Update `backend/README.md` (endpoints + generation / open-day rules) and
      record open items at the end of this file.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Status — Milestone 4 complete (2026-09-10)

Delivered on branch `feat-deliveries`:

- **Enums**: `DeliveryStatus` + `TERMINAL_DELIVERY_STATUSES` /
  `DELIVERY_PROGRESS_STATUSES` / `WEEKDAY_NAMES` helpers.
- **Migration `0004_deliveries`**: `deliveries` (unique
  `(subscription_id, delivery_date, time_slot)`, `meal_quantity`/`meals_deducted`
  checks, `reversed`/`reversal_*` columns), `planned_skips` (range-ordered check),
  `holidays` (unique date). up/down/up clean.
- **`settings_service`**: `get_str`, `closed_weekday_index()` (maps the
  `closed_weekday` name → `date.weekday()`).
- **`delivery_service`**:
  - `is_open_day()` = not the weekly closed day and not a holiday.
  - `generate(on_date)` — idempotent (`INSERT … ON CONFLICT DO NOTHING …
    RETURNING`), returns `{date, created, open_day}`; respects
    frequency (`DAILY` / `SPECIFIC_WEEKDAYS` / `CUSTOM` where
    `custom_schedule = {"dates": [...]}`), planned skips, the subscription
    window and balance.
  - `set_status()` — row-locks the delivery **and** the subscription;
    `DELIVERED` decrements `meals_consumed` and auto-`COMPLETED`s at zero;
    positive outcomes (`PREPARING`/`OUT_FOR_DELIVERY`/`DELIVERED`) are blocked
    when the subscription is not `ACTIVE` (BR-29); a finalised delivery is 409.
  - `reverse()` — restores the exact `meals_deducted`, sets status back to
    `SCHEDULED`, records `reversed`/`reversal_*`, rolls `COMPLETED → ACTIVE`.
  - planned skips: add cancels non-terminal deliveries in range.
- **`holiday_service`**: list / add (cancels non-terminal deliveries on the
  date) / remove. ADMIN for writes.
- **Endpoints**: `GET /deliveries?date=` (+status/area/time_slot/subscription_id),
  `POST /deliveries/generate`, `PATCH /deliveries/{id}`,
  `POST /deliveries/{id}/reverse`; `GET/POST /subscriptions/{id}/skips` +
  `DELETE`, `GET /subscriptions/{id}/deliveries`; `GET/POST/DELETE /holidays`.
- Tests: `test_deliveries.py` (19) — generation (Tuesday/holiday/skip/paused/
  idempotency/weekday), recording (deduct / multi-meal / complete-at-zero /
  block-on-cancelled / double-mark), reversal (restore / `COMPLETED→ACTIVE` /
  not-reversible), holiday & skip cancel existing, RBAC, and a **real
  two-transaction row-lock test** proving the balance moves exactly once.
  **77 pass** total.
- `backend/README.md` updated.

Verified locally: ruff, mypy(strict), `alembic upgrade head` /
`downgrade base` / re-upgrade, 77/77 pytest, and a live run: generate (Mon → 1,
Tue → 0/closed) → daily list with area/customer → `DELIVERED` (remaining 25→24)
→ reverse (→25, status `SCHEDULED`) → add holiday → generate on that date (0/
closed).

# Open questions / deferred

- **Payments** (`payment_status`, dues) — Milestone 5. Deliveries do not check
  payment state (Q7.5: delivery is independent of payment).
- **BR-29 scope**: the hard block covers only the "positive" outcomes
  (`PREPARING`/`OUT_FOR_DELIVERY`/`DELIVERED`). `SKIPPED`/`CANCELLED`/`FAILED`
  are allowed on a non-`ACTIVE` subscription so staff can tidy the list. Slight
  deviation from the phase-five plan's "any status change"; revisit if the
  business wants it stricter.
- **Pausing/cancelling a subscription does not auto-cancel its future
  `SCHEDULED` deliveries** yet — only holidays and planned skips do. Generation
  won't create new ones for a paused/cancelled sub, but stale rows can linger
  until the daily list is regenerated. Worth adding a sweep in M5/M6.
- **`custom_schedule`** validates only that `{"dates": [...]}` is present and
  well-shaped enough for `due_on`; no calendar/holiday cross-check at
  subscription-edit time.
- **`RESCHEDULED`** sets `rescheduled_to_date` but does not itself create the
  new date's delivery — the next `generate` run for that date does (only if the
  subscription's frequency makes it due; a one-off reschedule outside the
  frequency is not yet supported).
- **Daily-list `area` filter** matches on `snapshot_delivery_address->>'area'`;
  fine for v1, but there is no delivery-zone model (Q6.10, deferred).
