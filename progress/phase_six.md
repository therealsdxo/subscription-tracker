# Goals

1. You're the senior backend engineer continuing HealthX. Work strictly from
   `project.md`, `progress/questionnaire.md`, `progress/tech_doc.md`, and the code
   on `main` (Milestones 1–4). Keep the established patterns: routers → services
   (transactional, own every invariant) → repositories → models; Pydantic schemas
   per resource; `audit_service.record()` for sensitive actions; ADMIN/STAFF
   guards from `app.core.deps`; explicit enum create/drop in migrations;
   `alembic upgrade`/`downgrade` clean on a fresh database.

2. Deliver **Milestone 5 — Payments** (`tech_doc.md` §16, §4.6, §7). Payments and
   refunds are recorded against a **subscription** (which already carries the
   snapshotted `snapshot_final_price`). Payment state **never** gates activation
   or delivery recording (BR-27, Q7.5) — it is surfaced as information only. This
   phase also fills the M3-deferred payment fields on the subscription responses.

3. Enums (`app/models/enums.py`):
   - `PaymentMethod`: `CASH`, `UPI`, `CARD`, `BANK_TRANSFER`, `OTHER` (Q7.4).
   - `PaymentStatus`: `UNPAID`, `PARTIALLY_PAID`, `PAID`, `REFUNDED` (BL-18).
     **Derived, never stored** — computed from the payment/refund rows.

4. Migration `0005_payments` (`tech_doc.md` §3.3):
   - `payments`: `id`, `subscription_id` FK (ondelete RESTRICT), `amount`
     `NUMERIC(10,2)` (check `> 0`), `payment_method` enum, `reference_number`
     (nullable), `payment_date` (date, not null), `notes` (nullable),
     `recorded_by` FK users (nullable), `created_at`. Index `(subscription_id)`.
     Only successful payments are ever inserted (no status column).
   - `refunds`: `id`, `subscription_id` FK (ondelete RESTRICT), `amount`
     `NUMERIC(10,2)` (check `> 0`), `refund_date` (date, not null), `reason`
     (**not null**), `payment_method` enum (how it was returned),
     `reference_number` (nullable), `recorded_by` FK users (nullable),
     `created_at`. Index `(subscription_id)`.

5. Derived payment view — a `payment_service` helper
   `summary(session, subscription) -> PaymentSummary` (`tech_doc.md` §4.6):
   - `total_paid = Σ payments.amount`
   - `total_refunded = Σ refunds.amount`
   - `net_paid = total_paid - total_refunded`
   - `outstanding_amount = max(snapshot_final_price - net_paid, 0)`
   - `payment_status`:
     - `REFUNDED` if `total_refunded > 0`
     - else `UNPAID` if `total_paid == 0`
     - else `PARTIALLY_PAID` if `0 < net_paid < snapshot_final_price`
     - else `PAID` if `net_paid >= snapshot_final_price`
   - `suggested_refund = round(snapshot_final_price * meals_remaining /
     meals_allocated, 2)` — **guidance only** (`tech_doc.md` §7); never applied
     automatically.
   - Provide a batched variant for lists so `N+1` queries are avoided.

6. Recording a payment — `payment_service.record_payment(...)` — STAFF:
   - `{amount, payment_method, payment_date?, reference_number?, notes?}`.
   - `amount > 0`; `payment_date` defaults to today, may be back-dated (late
     entry), not future-dated.
   - Allowed against a subscription in **any** status (a late payment on a
     `CANCELLED` / `COMPLETED` subscription is legitimate).
   - `audit PAYMENT_RECORDED`.

7. Issuing a refund — `payment_service.issue_refund(...)` — **ADMIN only**
   (`tech_doc.md` §5.2, §7):
   - `{amount, refund_date?, reason, payment_method, reference_number?}`.
   - `reason` is mandatory; `amount > 0`.
   - **Guard**: the refund must not push `net_paid` negative — reject with 422
     `REFUND_EXCEEDS_PAID` if `amount > net_paid` at the time of issue.
   - No automatic proration; the `suggested_refund` figure is available on the
     subscription/payment views for the operator to reference.
   - `audit REFUND_ISSUED`.

8. Wire the derived view into existing responses:
   - `SubscriptionOut` / `SubscriptionDetail` gain `payment_status`,
     `total_paid`, `net_paid`, `outstanding_amount`, `suggested_refund`.
   - `GET /subscriptions?dues=true` — subscriptions with
     `outstanding_amount > 0` (a correlated subquery on the snapshot price minus
     net paid); combinable with `status` / `customer_id`; paginated.
   - `CustomerDetail.subscriptions.current` already returns a `SubscriptionOut`,
     so it picks up the payment fields for free — confirm with a test.

9. Endpoints (`tech_doc.md` §8):
   - `POST /subscriptions/{id}/payments` `{...}` — record a payment. STAFF.
   - `GET /subscriptions/{id}/payments` — that subscription's payments +
     refunds + the derived summary.
   - `GET /payments` — all payments, filter `subscription_id` / `customer_id` /
     `method` / date range; paginated.
   - `GET /payments/{id}` — one payment.
   - `POST /subscriptions/{id}/refunds` `{...}` — issue a refund. ADMIN.
   - `GET /subscriptions/{id}/refunds` — that subscription's refunds.

10. Out of scope for this phase (confirm, don't build):
    - PDF / printable invoices & receipts (Q7.7) — a plain payment record view
      is enough for v1.
    - Hardcoded GST percentages / automatic tax computation (Q7.8) — the
      `base_price` / `tax_amount` / `final_price` snapshot fields already exist
      and are entered on the package.
    - Any payment/refund gating of subscription activation or delivery recording
      (BR-27) — deliveries stay independent.
    - The dashboard `outstanding_dues_total` tile — Milestone 6.

11. Tests (`pytest`) — priority order from Q1.7 (payment calculations):
    - `UNPAID` when no payments; `PARTIALLY_PAID` after a part payment;
      `PAID` when installments sum to ≥ `snapshot_final_price`;
      `outstanding_amount` math; overpayment → `outstanding_amount == 0`,
      status `PAID`.
    - `REFUNDED` once any refund exists; `net_paid` drops by the refund;
      `outstanding_amount` recomputed.
    - Refund guard: `amount > net_paid` → 422 `REFUND_EXCEEDS_PAID`.
    - Payment allowed on a `CANCELLED` subscription; delivery recording still
      works while a subscription is `UNPAID` (BR-27).
    - RBAC: STAFF can record a payment, STAFF cannot issue a refund (403).
    - `GET /subscriptions?dues=true` returns only subscriptions with an
      outstanding balance.
    - `suggested_refund` = `final_price * meals_remaining / meals_allocated`
      (rounded), and is not auto-applied.
    - Audit rows: `PAYMENT_RECORDED`, `REFUND_ISSUED`.

12. Deliverables check:
    - `alembic upgrade head` → `downgrade base` → re-`upgrade` clean on a fresh DB.
    - `make check` (ruff + mypy strict + pytest) green.
    - New endpoints in `/docs`; a manual run: create subscription → record two
      part payments (status `PARTIALLY_PAID` → `PAID`) → issue a refund
      (status `REFUNDED`, `outstanding` recomputed) → `GET /subscriptions?dues=true`.
    - Update `backend/README.md` (endpoints + the derived payment view) and
      record open items at the end of this file.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Open questions / deferred

_(fill in during the work)_
