# Feature — multiple delivery time slots per subscription

## Request

> "there is one addition which I wish to make a single customer can have
> multiple deliveries on a single day"

The system already let a customer end up with more than one delivery a day —
but only if they had two separate concurrent subscriptions, e.g. one
`MORNING` subscription and one `EVENING` subscription. That path turned out
to be a dead end: `subscriptions` carries a **partial unique index** —
at most one `ACTIVE` row per `customer_id` (`tech_doc.md` §3.3) — so a second
subscription for an already-active customer is created `PENDING` and queued,
never concurrently `ACTIVE`. Two deliveries a day for one customer was
therefore not actually achievable without this change.

Presented three options (ad-hoc one-off delivery, multiple time slots per
subscription, or "already sufficient via two subscriptions" — which the
constraint above rules out). Chosen: **multiple time slots per subscription**.
A subscription now carries a *list* of delivery time slots instead of one; the
daily generator produces one delivery per slot per due day. One subscription,
one meal balance, one payment/lifecycle — just more delivery rows.

## Changes

### Backend

- `subscriptions.delivery_time_slot` (single enum) → `delivery_time_slots`
  (enum array, not null, ≥ 1 entry, no duplicates).
  - Migration `0006_multi_time_slot`: add the array column, backfill from the
    old column (`ARRAY[delivery_time_slot]`), make it `NOT NULL`, drop the old
    column. Reversible (`downgrade()` does the inverse, taking `[1]`).
- `SubscriptionCreate` / `SubscriptionRenew` (`app/schemas/subscription.py`,
  shared via `_DeliveryConfig`) and `SubscriptionUpdate` take
  `delivery_time_slots: list[TimeSlot]`. A shared `_check_time_slots()`
  validator enforces: at least one slot, no repeats, and
  `delivery_time_slot_note` is required if `CUSTOM` is among the slots (one
  shared note, not per-slot — see Deferred).
- `delivery_service.generate()` (`app/services/delivery_service.py`) loops
  `for slot in sub.delivery_time_slots` and inserts one `Delivery` per slot,
  each still going through the existing
  `on_conflict_do_nothing(index_elements=[subscription_id, delivery_date,
  time_slot])` — that unique constraint was already scoped per slot, so it
  needed no change to allow multiple rows per subscription per day.
  `qty = min(meals_per_delivery, meals_remaining)` is computed once per
  subscription per generation run and reused for every slot; the actual
  balance deduction still happens independently per delivery when it's marked
  `DELIVERED` (`_apply_status`), so an under-provisioned balance is capped at
  record time, not generation time.
- `import_service.py` (CSV bulk import): its single `time_slot` column now
  maps to a one-element `delivery_time_slots` list — the CSV format itself is
  unchanged (see Deferred).
- `tech_doc.md` §3.3 (`subscriptions` table), §6.1 (generation pseudocode),
  §8.2 (create-subscription example) updated to match.

### Frontend

- Regenerated `lib/api/schema.d.ts` (`pnpm gen:api`) against the updated
  OpenAPI schema.
- `subscription-form-dialog.tsx` (create/renew): the time-slot picker changed
  from a single `<Select>` to a multi-select chip toggle group — the same
  pattern already used for the `SPECIFIC_WEEKDAYS` weekday picker. A caption
  under it ("Pick more than one slot to deliver to this customer multiple
  times a day") makes the new capability discoverable. Submit is blocked with
  a toast if zero slots are selected, or if `CUSTOM` is picked without a note.
- `subscriptions/[id]/page.tsx` (detail): "Time slot" row → "Time slots",
  rendering `delivery_time_slots.join(", ")`.

## Verification

- Backend: 112/112 tests pass (`uv run pytest`, against a Postgres instance on
  `:5432`/`healthx_test` since the docker-compose `db_test` service on `:5433`
  isn't running in this environment), `ruff check` and `mypy` clean.
- Frontend: `lint` / `typecheck` / `vitest` (7/7) / `build` all clean.
- Live smoke test through the running stack: created a package + customer,
  created a subscription with `delivery_time_slots: [MORNING, EVENING]`,
  called `POST /deliveries/generate` for today → `created: 2`, both rows
  correctly carrying `subscription_id`/`customer_id` of the one subscription;
  re-running generation for the same date → `created: 0` (idempotent).
  Confirmed visually in the browser: the create dialog's chip picker, and the
  subscription detail page showing "Time slots: MORNING, EVENING" with both
  delivery rows listed under "Recent deliveries". Test data cleared back to
  the seeded admin afterward.

## Open questions / deferred

- **One shared `delivery_time_slot_note`, not per-slot.** If a subscription
  has both a `CUSTOM` slot and, say, `MORNING`, the one note has to describe
  the `CUSTOM` slot only — there's no per-slot note field. Fine for the
  common case (one `CUSTOM` slot at most) but would need a schema change
  (note keyed by slot) if a subscription ever needs two differently-described
  custom slots.
- **No per-slot `meals_per_delivery` override.** Every slot on a subscription
  gets the same `meals_per_delivery` quantity — a 2-meals-per-day
  MORNING+EVENING split (1 meal each) isn't expressible without adding two
  meals to *each* slot's delivery. Would need a per-slot quantity map if that
  granularity is ever wanted.
- **No delivery-settings edit dialog in the UI yet.** `SubscriptionUpdate`
  already accepts a new `delivery_time_slots` list (validated the same way as
  create/renew), so an existing subscription's slots *can* be changed via the
  API today — there's just no dialog on the subscription detail page for it
  yet (noted as deferred back in the "complete the frontend" work too).
- **CSV import stays single-slot.** `_build_subscription_fields` still reads
  one `time_slot` CSV column and wraps it as a one-element list; multi-slot
  subscriptions can't be expressed via bulk import without a CSV format change
  (e.g. a semicolon-separated slot list, mirroring how `delivery_weekdays`
  already does comma-separated).
