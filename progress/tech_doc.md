# HealthX — Technical Documentation (v1)

Status: Draft for build kick-off
Owner: Engineering
Sources: `project.md`, `progress/questionnaire.md` (Phase Zero, fully answered)
Last updated: 2026-09-10

---

## 1. Purpose & Context

**HealthX** is an internal, centralized meal-subscription management system for a
healthy meal-delivery business. It is the **single source of truth** for
customers, meal packages, subscriptions, deliveries, and payments.

It replaces manual / spreadsheet tracking and prevents the operational errors
that manual tracking causes:

- Incorrect meal counts / remaining balances
- Meals delivered after a subscription has expired or completed
- Missed deliveries
- Wrong expiry calculations
- Difficulty finding active customers, dues, and history

v1 is an **operations tool for internal staff only**. There is no customer-facing
portal.

### 1.1 In scope for v1

- Customer management (create, update, search, soft-delete, multiple addresses)
- Meal package management (create, edit, activate/deactivate, hard-delete if unused)
- Subscription lifecycle (create, activate, pause/resume, extend, complete, expire, cancel, renew)
- Package-value snapshotting onto subscriptions
- Daily delivery list generation + delivery outcome recording + reversal
- Meal-balance tracking and manual adjustments (audited)
- Payments (multiple installments) + refunds (manual)
- Business closed-days: Tuesdays + maintainable holiday calendar
- Planned customer skip dates
- Dashboard with core operational counts
- Monitoring lists: active / completed / expired / expiring-soon / dues
- CSV export (customers, subscriptions, payments, daily deliveries)
- CSV bulk import of existing customers (+ current subscription where possible)
- Audit log of sensitive actions
- Role-based access (ADMIN, STAFF)
- Basic in-dashboard expiry alerts

### 1.2 Out of scope for v1 (deferred to v2+)

- WhatsApp / SMS / email notifications and automated reminders
- Customer-facing portal
- Route optimization / driver assignment / delivery sequencing
- Analytics / BI / churn prediction
- PDF invoices / receipts (printable payment record may come later)
- Automatic refund calculation (a prorated figure may be *shown* as a suggestion only)
- Offline mode

---

## 2. Architecture

### 2.1 High-level

```
┌─────────────────────┐     HTTPS/JSON      ┌──────────────────────┐
│  Next.js Web App     │  ───────────────▶   │  FastAPI REST API     │
│  React + TypeScript  │  ◀───────────────   │  Pydantic + services  │
│  Tailwind CSS        │                     └──────────┬───────────┘
└─────────────────────┘                                │ SQLAlchemy 2.x
                                                        │ + Alembic
                                             ┌──────────▼───────────┐
                                             │  PostgreSQL           │
                                             │  (RDS in production)  │
                                             └──────────────────────┘

  EventBridge Scheduler ──▶ daily job (activate PENDING, expire overdue,
                                        refresh alert lists)
```

Layering inside the backend:

```
API routers (HTTP, auth, request/response schemas)
      │
Services / business rules  ◀── the only place domain invariants live
      │
Repositories (query/persistence helpers)
      │
SQLAlchemy models  ──  PostgreSQL
```

Business logic must not live in routers or in the ORM models. All invariants
(expiry, meal balance, status transitions, delivery eligibility) are enforced in
the service layer inside a database transaction.

### 2.2 Technology stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS | Responsive; desktop-first, tablet/mobile secondary |
| Backend | Python 3.13, FastAPI, Pydantic v2 | API-first, REST/JSON |
| ORM / migrations | SQLAlchemy 2.x, Alembic | Replaces the in-memory `tools.py` prototype entirely |
| Database | PostgreSQL 16 (dev **and** prod) | No SQLite |
| Auth | Email + password, Argon2id hashing, JWT (short-lived access + refresh) | Staff only |
| Package mgmt | `uv` | Existing repo tooling |
| Tests | `pytest` | See §12 |
| Hosting | AWS, region `ap-south-1` (Mumbai) | See §11 |
| Timezone | `Asia/Kolkata` everywhere; timestamps stored UTC, business dates as `DATE` | |
| Currency | INR only | `NUMERIC(10,2)` |

### 2.3 Existing code

`tools.py` and the `src/subscription_tracker` CLI stub are throwaway prototypes.
They are **replaced**, not extended. The persistence layer is PostgreSQL via
SQLAlchemy.

---

## 3. Domain Model

### 3.1 Entity-relationship overview

```
User ────────────────┐ (created_by / performed_by on many tables)
                      │
Customer 1 ───── N CustomerAddress
   │ 1
   │
   N
Subscription  N ─────── 1 Package        (package_id = reference only;
   │                                       authoritative values are snapshotted)
   ├── 1 ── N Delivery
   ├── 1 ── N Payment
   ├── 1 ── N Refund
   ├── 1 ── N MealAdjustment
   ├── 1 ── N SubscriptionEvent   (pause/resume/extend/status changes)
   ├── 1 ── N PlannedSkip
   └── previous_subscription_id ──▶ Subscription  (renewal chain)

Holiday        (business closed dates, standalone)
Setting        (configurable thresholds / formats, standalone)
AuditLog       (actor = User, polymorphic entity reference)
```

Cardinal decisions from Phase Zero:

- **Normalized model.** Customer identity stays on `Customer`. Package, meal
  balance, payment status, dates, and status belong to `Subscription`. A customer
  has **many** subscriptions over time (full renewal history). (Q0.1)
- **Soft delete** for customers — hide from normal operations, keep all history.
  (Q0.2)
- `resubscribe_number` is **not** stored as mutable customer data. It is derived:
  `subscription_number = ordinal of this subscription among the customer's
  subscriptions`, first = 1. (Q8.4)
- One **ACTIVE** subscription per customer at a time; a renewal can sit in
  **PENDING** and start when the current one ends. (Q5.1, Q8.2)

### 3.2 Identifiers

Human-readable codes are system-generated from a per-entity sequence, zero-padded,
prefix + width configurable via `Setting`:

| Entity | Format | Example |
|---|---|---|
| Customer | `CUST-` + 6 digits | `CUST-000001` |
| Package | `PKG-` + 5 digits | `PKG-00001` |
| Subscription | `SUB-` + 6 digits | `SUB-000001` |

Internal primary keys are `BIGINT` surrogate keys. Codes are unique, immutable,
and used in the UI and exports.

### 3.3 Tables

Common columns on mutable business tables: `created_at`, `updated_at`,
`created_by`, `updated_by` (all timestamps `timestamptz`, user refs FK → `users`).

#### `users`

| Column | Type | Constraints / notes |
|---|---|---|
| id | bigint PK | |
| email | citext | unique, not null |
| password_hash | text | not null (Argon2id) |
| full_name | text | not null |
| role | enum `user_role` | `ADMIN` \| `STAFF`, not null |
| is_active | bool | default true |
| last_login_at | timestamptz | nullable |
| created_at / updated_at | timestamptz | |

Password policy v1: minimum length 10, not a common password, no forced rotation,
no 2FA (documented as a v2 candidate). Auth throttling: see §5.

#### `customers`

| Column | Type | Constraints / notes |
|---|---|---|
| id | bigint PK | |
| customer_code | text | unique, not null (`CUST-000001`) |
| name | text | not null |
| phone | text | not null, **unique** |
| email | citext | nullable, **unique when present** |
| default_dietary_preference | enum `dietary_pref` | nullable — `VEGETARIAN`, `NON_VEGETARIAN`, `EGGETARIAN`, `VEGAN`, `JAIN`, `OTHER` |
| dietary_notes | text | nullable |
| allergies | text | nullable — kept **separate** from preference (operationally important) |
| notes | text | nullable |
| is_active | bool | default true (soft-delete flag) |
| deactivated_at | timestamptz | nullable |
| deactivated_by | bigint FK users | nullable |
| deactivation_reason | text | nullable |

Required on create: **name, phone, delivery address** (at least one address).
Email is optional. (Q0.4, Q3.2)

Duplicate warning (non-blocking): on create/update, if `name` closely matches an
existing active customer with the same or similar `phone`, the API returns a
`warnings` array; staff can proceed. Exact `phone`/`email` collisions are hard
unique-constraint errors.

#### `customer_addresses`

A customer can have **multiple** addresses. (Q3.4)

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| customer_id | bigint FK customers | not null, on delete restrict |
| label | text | e.g. "Home", "Office" |
| address_line | text | not null |
| area | text | not null (locality; useful for future zoning) |
| city | text | not null |
| pincode | text | not null |
| landmark | text | nullable |
| delivery_notes | text | nullable |
| is_primary | bool | exactly one primary per customer (partial unique index) |
| is_active | bool | default true |

#### `packages`

| Column | Type | Constraints / notes |
|---|---|---|
| id | bigint PK | |
| package_code | text | unique, not null (`PKG-00001`) |
| name | text | not null |
| description | text | nullable (optional on create) |
| number_of_meals | int | not null, **1–500** |
| validity_days | int | not null, **1–730** |
| base_price | numeric(10,2) | not null, **≥ 0** |
| tax_amount | numeric(10,2) | not null, default 0 (GST **not** hardcoded) |
| final_price | numeric(10,2) | not null, = `base_price + tax_amount` (stored, validated) |
| status | enum `package_status` | `ACTIVE` \| `INACTIVE`, default `ACTIVE` |

Rules:

- **Editing a package never affects existing subscriptions** — values are
  snapshotted at subscription creation. (BL-17, Q4.4)
- A package **used by any subscription** can only be **deactivated**, never
  deleted. (BL-16, Q4.5)
- A package **never used** by any subscription may be **hard-deleted** by an
  ADMIN. (Q4.5)
- `INACTIVE` packages cannot be assigned to new subscriptions.

#### `subscriptions`

| Column | Type | Constraints / notes |
|---|---|---|
| id | bigint PK | |
| subscription_code | text | unique, not null (`SUB-000001`) |
| customer_id | bigint FK customers | not null |
| package_id | bigint FK packages | not null — **reference only** |
| subscription_number | int | per-customer ordinal (1, 2, 3…); stored for reporting, reconciled with `count()` |
| status | enum `subscription_status` | `PENDING` \| `ACTIVE` \| `PAUSED` \| `COMPLETED` \| `EXPIRED` \| `CANCELLED` |
| start_date | date | not null; may be back-dated, current, or future-dated |
| original_end_date | date | not null; `start_date + snapshot_validity_days` at creation |
| expected_end_date | date | not null; `original_end_date` adjusted by extensions and pauses |
| actual_end_date | date | nullable; set when `COMPLETED` / `EXPIRED` / `CANCELLED` |
| **snapshot** — `snapshot_package_name` | text | copied at creation |
| `snapshot_package_description` | text | copied at creation (nullable) |
| `snapshot_number_of_meals` | int | copied at creation |
| `snapshot_validity_days` | int | copied at creation |
| `snapshot_base_price` | numeric(10,2) | copied at creation |
| `snapshot_tax_amount` | numeric(10,2) | copied at creation |
| `snapshot_final_price` | numeric(10,2) | copied at creation — the price this subscription owes |
| meals_allocated | int | = `snapshot_number_of_meals` |
| meals_consumed | int | default 0 |
| meals_adjustment | int | default 0 — signed net of manual adjustments |
| meals_remaining | int | **generated**: `meals_allocated + meals_adjustment - meals_consumed` |
| delivery_frequency | enum `delivery_frequency` | `DAILY` \| `SPECIFIC_WEEKDAYS` \| `CUSTOM` |
| delivery_weekdays | int[] | ISO weekdays 1–7, required when `SPECIFIC_WEEKDAYS` |
| custom_schedule | jsonb | required when `CUSTOM` (list of dates or rule) |
| meals_per_delivery | int | default 1, ≥ 1 |
| delivery_time_slot | enum `time_slot` | `MORNING` \| `LUNCH` \| `EVENING` \| `CUSTOM` |
| delivery_time_slot_note | text | nullable (for `CUSTOM`) |
| delivery_address_id | bigint FK customer_addresses | the address chosen for this subscription |
| snapshot_delivery_address | jsonb | address fields copied at creation (can differ per subscription) (Q3.5) |
| snapshot_dietary_preference | enum `dietary_pref` | copied from customer at creation, overridable |
| subscription_notes | text | nullable |
| previous_subscription_id | bigint FK subscriptions | nullable — renewal chain |
| cancelled_at / cancelled_by / cancellation_reason | | set on cancel |

Constraints / indexes:

- **Partial unique index**: at most one row per `customer_id` with
  `status = 'ACTIVE'`.
- Check: `meals_per_delivery >= 1`, `snapshot_number_of_meals >= 1`.
- Index on `(status, expected_end_date)` for expiry/alert queries.
- Index on `(customer_id, status)`.

`payment_status` and `outstanding_amount` are **derived**, not stored (see §7).

#### `subscription_events`

Immutable log of lifecycle actions on a subscription.

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| event_type | enum | `CREATED`, `ACTIVATED`, `PAUSED`, `RESUMED`, `EXTENDED`, `COMPLETED`, `EXPIRED`, `CANCELLED`, `RENEWED` |
| reason | text | required for `PAUSED`, `EXTENDED`, `CANCELLED` |
| effective_date | date | |
| pause_start / pause_end / paused_days | | set for pause/resume |
| old_expected_end_date / new_expected_end_date | date | set for `EXTENDED` and `RESUMED` |
| performed_by | bigint FK users | not null |
| performed_at | timestamptz | not null |

#### `meal_adjustments`

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| quantity | int | signed, non-zero |
| reason | text | **not null** |
| performed_by | bigint FK users | ADMIN only |
| performed_at | timestamptz | |

Applying an adjustment updates `subscriptions.meals_adjustment` in the same
transaction and writes an `audit_logs` row.

#### `deliveries`

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| customer_id | bigint FK | denormalized for the daily list |
| delivery_date | date | not null |
| time_slot | enum `time_slot` | from subscription, overridable per delivery |
| status | enum `delivery_status` | `SCHEDULED`, `PREPARING`, `OUT_FOR_DELIVERY`, `DELIVERED`, `SKIPPED`, `CANCELLED`, `FAILED`, `RESCHEDULED` |
| meal_quantity | int | planned meals for this delivery (default `meals_per_delivery`) |
| meals_deducted | int | default 0 — actual meals removed from balance (for exact reversal) |
| delivered_at | timestamptz | set when `DELIVERED` |
| recorded_by | bigint FK users | who set the final status |
| reversed | bool | default false |
| reversal_reason | text | required when reversing |
| reversed_by / reversed_at | | |
| rescheduled_to_date | date | set when `RESCHEDULED` |
| notes | text | nullable |

Constraints:

- **Unique `(subscription_id, delivery_date, time_slot)`** — prevents duplicate
  rows and double-marking under concurrency.
- Only `DELIVERED` changes the meal balance (§6). `meals_deducted` records what
  was actually removed so reversal is exact.

#### `planned_skips`

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| skip_date_from | date | not null |
| skip_date_to | date | not null (single day → same value) |
| reason | text | nullable |
| created_by / created_at | | |

Delivery generation does not create `SCHEDULED` deliveries on covered dates.

#### `holidays`

Maintainable business-closed calendar. **Tuesday closure is a system rule**
(config key `closed_weekday`), not a row here. Specific one-off closures go here.

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| holiday_date | date | unique, not null |
| name | text | not null |
| created_by / created_at | | ADMIN only |

#### `payments`

Only successful payments are recorded. Subscription → many payments. (Q7.1, Q7.2)

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| amount | numeric(10,2) | > 0 |
| payment_method | enum `payment_method` | `CASH`, `UPI`, `CARD`, `BANK_TRANSFER`, `OTHER` |
| reference_number | text | nullable |
| payment_date | date | not null |
| notes | text | nullable |
| recorded_by | bigint FK users | STAFF or ADMIN |
| created_at | timestamptz | |

#### `refunds`

Manual only — **no automatic calculation** (Q7.6). ADMIN only.

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| subscription_id | bigint FK | not null |
| amount | numeric(10,2) | > 0 |
| refund_date | date | not null |
| reason | text | **not null** |
| payment_method | enum `payment_method` | how it was returned |
| reference_number | text | nullable |
| recorded_by | bigint FK users | ADMIN only |
| created_at | timestamptz | |

#### `audit_logs`

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| actor_id | bigint FK users | nullable (system jobs → null) |
| action | text | e.g. `PACKAGE_UPDATED`, `SUBSCRIPTION_EXTENDED`, `DELIVERY_REVERSED`, `PAYMENT_RECORDED`, `REFUND_ISSUED`, `CUSTOMER_DEACTIVATED`, `MEAL_ADJUSTED` |
| entity_type | text | `customer`, `package`, `subscription`, `delivery`, `payment`, `refund`, `user` |
| entity_id | bigint | |
| before | jsonb | nullable |
| after | jsonb | nullable |
| metadata | jsonb | reason, request id, etc. |
| ip_address | inet | nullable |
| created_at | timestamptz | not null |

Audited at minimum (Q2.6): package modifications, subscription extensions,
subscription cancellations, meal adjustments, delivery reversals, payments,
refunds, customer deletion/deactivation. Audit rows are never updated or deleted.

#### `settings`

Key/value config so operational thresholds don't require a deploy.

| key | default | meaning |
|---|---|---|
| `closed_weekday` | `TUESDAY` | weekly no-delivery day |
| `expiry_days_threshold` | `7` | "expiring soon" if `expected_end_date - today ≤ N` |
| `expiry_meals_threshold` | `5` | "expiring soon" if `meals_remaining ≤ N` |
| `customer_code_prefix` / `_width` | `CUST-` / `6` | |
| `package_code_prefix` / `_width` | `PKG-` / `5` | |
| `subscription_code_prefix` / `_width` | `SUB-` / `6` | |

---

## 4. Business Rules (consolidated)

Rules from `project.md` (BL-01…BL-18) plus Phase Zero clarifications. Where the
two conflicted, the questionnaire answer wins.

### 4.1 Identifiers & records

- **BR-1** Customer, package, and subscription codes are system-generated and
  immutable (§3.2).
- **BR-2** Customer requires name, phone, and at least one delivery address.
  Email is optional but unique when present. Phone is unique. (BL-01 amended by
  Q0.4)
- **BR-3** Customers are **soft-deleted** (`is_active = false`) — never
  hard-deleted while history exists. Deactivation needs a reason and is audited.
  Historical subscriptions, deliveries, and payments remain intact and visible in
  the customer's history. (BL-04 amended by Q0.2)

### 4.2 Packages

- **BR-4** Package requires name, number_of_meals (1–500), validity_days (1–730),
  base_price (≥ 0). Description optional. Default status `ACTIVE`. (BL-05, Q4.6,
  Q4.7)
- **BR-5** Editing a package applies only to **new** subscriptions. Existing
  subscriptions are unaffected because critical values are snapshotted. (BL-17,
  Q4.4)
- **BR-6** A package that has been used in ≥ 1 subscription can only be set
  `INACTIVE`. Never used → ADMIN may hard-delete. (BL-16, Q4.5)
- **BR-7** `INACTIVE` packages cannot be assigned to new subscriptions. (BL-16)

### 4.3 Subscription creation & snapshot

- **BR-8** On creation the subscription copies from the package:
  `name, description, number_of_meals, validity_days, base_price, tax_amount,
  final_price`. It also snapshots the chosen delivery address and the customer's
  dietary preference. (BL-17, Q5.5, Q5.6)
- **BR-9** `meals_allocated = snapshot_number_of_meals`. (BL-06)
- **BR-10** `original_end_date = start_date + snapshot_validity_days` (calendar
  days). `expected_end_date` starts equal to `original_end_date`. (BL-09, Q4.3,
  Q0.5)
  - **Example:** 25-meal / 50-day package, `start_date = 2026-09-01` →
    `original_end_date = 2026-10-21`. The subscription is valid **through**
    2026-10-21.
  - **Tuesdays and holidays count toward validity** and do **not** extend it
    automatically. (Q0.5, Q4.3)
- **BR-11** `start_date` may be back-dated, today, or future-dated. Who created
  or changed the subscription is always logged. (Q5.3)
- **BR-12** A `start_date` on a Tuesday is allowed; validity still begins that
  day even though there is no delivery. (Q5.4)
- **BR-13** At most one `ACTIVE` subscription per customer. A new subscription
  created while one is still active is `PENDING` and starts when the current one
  reaches `COMPLETED`/`EXPIRED`/`CANCELLED`. Meal balances are never combined.
  (Q5.1, Q8.2)
- **BR-14** `subscription_number` = ordinal among the customer's subscriptions,
  first = 1 (replaces `resubscribe_number`). (Q8.4)

### 4.4 Meal balance

- **BR-15** `meals_remaining = meals_allocated + meals_adjustment -
  meals_consumed` (single rule; BL-07 and BL-12 were duplicates — Q0.3).
- **BR-16** A **`DELIVERED`** delivery consumes `meal_quantity` meals:
  `meals_consumed += meal_quantity`. A delivery may carry more than one meal
  (e.g. lunch + dinner → `meal_quantity = 2`). (BL-13, Q6.2)
- **BR-17** `SKIPPED`, `CANCELLED`, `FAILED`, `RESCHEDULED`, `SCHEDULED`,
  `PREPARING`, `OUT_FOR_DELIVERY` never change the balance and never extend
  expiry. (BL-14, Q6.5)
- **BR-18** Manual meal adjustments are **ADMIN only**, require a quantity and a
  reason, and are audited (timestamp + user). They move `meals_adjustment`.
  (Q5.12)

### 4.5 Subscription status lifecycle

Statuses: `PENDING`, `ACTIVE`, `PAUSED`, `COMPLETED`, `EXPIRED`, `CANCELLED`.
(BL-15 + `PENDING` from Q8.2)

```
          create (customer already has ACTIVE)         create (no ACTIVE)
                        │                                      │
                        ▼                                      ▼
                     PENDING ───────── activate ───────────▶ ACTIVE
                        │  (start_date reached & slot free)     │
                        │                                       ├── pause ──▶ PAUSED ──┐
                        │                                       │                      │ resume
                        │                                       │◀─────────────────────┘
                        │                                       │
                        │                    meals_remaining==0 │──▶ COMPLETED  (terminal)
                        │                  today > expected_end  │──▶ EXPIRED    (extend → ACTIVE)
                        │                          cancel(ADMIN) │──▶ CANCELLED  (terminal)
                        └── cancel(ADMIN) ─────────────────────────▶ CANCELLED
```

- **BR-19 COMPLETED** when `meals_remaining == 0`, even before `expected_end_date`.
  No further deliveries. Only a renewal continues service. (BL-10, Q5.8)
- **BR-20 EXPIRED** when `today > expected_end_date` and status was
  `ACTIVE`/`PAUSED`. Remaining meals are **forfeited**. (BL-11, Q5.9)
- **BR-21 Extend (ADMIN only).** Pushes `expected_end_date` out (by N days or to
  a new date). Requires a mandatory reason. The event records original expiry,
  new expiry, user, timestamp. Extending an `EXPIRED` subscription returns it to
  `ACTIVE` if the new date is in the future. (Q5.9)
- **BR-22 Pause.** ADMIN or STAFF. Requires a reason (travel / medical / customer
  request / temporary absence / other). On **resume**, `expected_end_date` is
  moved forward by the number of paused days. Deliveries are blocked while
  `PAUSED`. (Q5.10)
- **BR-23 Cancel (ADMIN only).** Requires a reason. Does **not** auto-calculate a
  refund; refunds are handled separately. (Q5.11, Q7.6)
- **BR-24 Status computation is hybrid.** `status` is stored, but expiry /
  completion is re-evaluated on every relevant read and write (view, delivery
  marking, payment, pause/resume). A daily scheduled job also sweeps for overdue
  expiries and PENDING activations. (Q5.7)

### 4.6 Payment status (derived)

- **BR-25** `total_paid = Σ payments.amount`; `total_refunded = Σ refunds.amount`;
  `net_paid = total_paid - total_refunded`;
  `outstanding_amount = max(snapshot_final_price - net_paid, 0)`. (Q7.3)
- **BR-26** `payment_status`:
  - `REFUNDED` if `total_refunded > 0`
  - else `UNPAID` if `total_paid == 0`
  - else `PARTIALLY_PAID` if `0 < net_paid < snapshot_final_price`
  - else `PAID` if `net_paid ≥ snapshot_final_price`
  (BL-18, Q7.3)
- **BR-27** Payment state **never blocks** activation or deliveries in v1.
  Outstanding dues are surfaced as a warning only. (Q7.5)

### 4.7 Deliveries & closed days

- **BR-28** No deliveries are generated or recorded on the configured
  `closed_weekday` (Tuesday) or on any `holidays` date. (project.md §1, Q6.7)
- **BR-29** Deliveries **cannot** be recorded against a subscription in
  `EXPIRED`, `COMPLETED`, `PAUSED`, or `CANCELLED` — hard block. This is the core
  problem the system exists to prevent. (Q6.8)
- **BR-30** A recorded `DELIVERED` can be **reversed** by an authorized user with
  a mandatory reason; the exact `meals_deducted` is restored and the action is
  audited. If the subscription had flipped to `COMPLETED` solely because of that
  delivery and is still within its validity window, it returns to `ACTIVE`.
  (Q6.6)
- **BR-31** Planned customer skip dates suppress delivery generation for the
  covered dates. (Q6.9)

### 4.8 Renewals

- **BR-32** A renewal creates a **new** subscription linked to the customer, with
  `previous_subscription_id` set. The old record is never reset. (BL — Q8.1)
- **BR-33** A renewal may use **any `ACTIVE` package** — not necessarily the
  previous one. (Q8.3)
- **BR-34** Renewing before the current subscription ends creates a `PENDING`
  subscription that activates when the current one closes. Meal balances are not
  carried forward or combined. (Q8.2, Q8.5)
- **BR-35** Unused meals do **not** transfer on renewal. An ADMIN may grant a
  goodwill `meal_adjustment` on the new subscription if warranted. (Q8.5)

---

## 5. Authentication & Authorization

### 5.1 Authentication

- Email + password. Passwords hashed with **Argon2id**.
- JWT: short-lived **access token** (~15 min) + longer **refresh token** (~7
  days, rotating). Refresh tokens are revocable (stored hashed server-side or as
  a denylist).
- All traffic over HTTPS. Auth endpoints are rate-limited (e.g. 10 attempts /
  5 min / IP + per-account lockout backoff).
- `last_login_at` updated on successful login.
- No self-signup — ADMIN creates users.

### 5.2 Roles & permission matrix

| Capability | STAFF | ADMIN |
|---|:---:|:---:|
| Login, view dashboard, view lists/details | ✅ | ✅ |
| Create / update customer | ✅ | ✅ |
| Manage customer addresses | ✅ | ✅ |
| Deactivate / reactivate customer | ❌ | ✅ |
| Search customers | ✅ | ✅ |
| Create subscription | ✅ | ✅ |
| Edit subscription (notes, address, schedule, slot) | ✅ | ✅ |
| Pause / resume subscription | ✅ | ✅ |
| Extend subscription | ❌ | ✅ |
| Cancel subscription | ❌ | ✅ |
| Manual meal adjustment | ❌ | ✅ |
| Renew subscription | ✅ | ✅ |
| Generate daily delivery list | ✅ | ✅ |
| Mark delivery outcome | ✅ | ✅ |
| Reverse a delivered delivery | ✅ | ✅ (audited) |
| Record planned skips | ✅ | ✅ |
| Create / edit / activate / deactivate package | ❌ | ✅ |
| Change package pricing / meals / validity | ❌ | ✅ |
| Hard-delete unused package | ❌ | ✅ |
| Record payment | ✅ | ✅ |
| Issue refund | ❌ | ✅ |
| Manage holiday calendar | ❌ | ✅ |
| Manage users | ❌ | ✅ |
| Edit settings / thresholds | ❌ | ✅ |
| View audit log | ❌ | ✅ |
| CSV export | ✅ | ✅ |
| CSV import (customers) | ❌ | ✅ |

(Q2.2, Q2.3) Permissions are enforced in the API (FastAPI dependency per route);
the frontend hides disallowed actions but is not the enforcement point.

### 5.3 Privacy (v1)

Customer contact data is restricted to authenticated staff, served only over
HTTPS, never exposed publicly. Store only what's needed. Sensitive admin actions
are logged. No formal GDPR workflow in v1. (Q3.7)

---

## 6. Delivery Workflow

### 6.1 Daily list generation

Triggered on demand (staff opens "Today's deliveries") and/or by the daily job.
Idempotent — safe to run repeatedly for the same date.

```
generate_deliveries(date D):
  if D.weekday == closed_weekday or D in holidays: return []   # BR-28
  for sub in subscriptions where status == ACTIVE
                            and start_date <= D <= expected_end_date
                            and meals_remaining > 0:
     if D within any planned_skip of sub: continue              # BR-31
     if not due_on(sub, D): continue        # frequency / weekday / custom rule
     qty = min(sub.meals_per_delivery, sub.meals_remaining)
     upsert delivery(sub, D, sub.delivery_time_slot)
        on conflict (subscription_id, delivery_date, time_slot) do nothing
        with status = SCHEDULED, meal_quantity = qty
```

`due_on`:
- `DAILY` → always (on an open day)
- `SPECIFIC_WEEKDAYS` → `D.isoweekday() in delivery_weekdays`
- `CUSTOM` → `D` matches `custom_schedule`

### 6.2 Recording an outcome

Staff move each row to a terminal status: `DELIVERED`, `SKIPPED`, `CANCELLED`,
`FAILED`, or `RESCHEDULED` (interim `PREPARING` / `OUT_FOR_DELIVERY` optional).

```
mark_delivered(delivery_id):
  BEGIN
    SELECT ... FROM subscriptions WHERE id = :sid FOR UPDATE   # row lock
    assert subscription.status == ACTIVE                       # BR-29
    assert today <= subscription.expected_end_date
    assert delivery.status not terminal                        # concurrency guard
    deducted = min(delivery.meal_quantity, subscription.meals_remaining)
    subscription.meals_consumed += deducted
    delivery.meals_deducted = deducted
    delivery.status = DELIVERED; delivery.delivered_at = now(); recorded_by = user
    if subscription.meals_remaining == 0:
        subscription.status = COMPLETED
        subscription.actual_end_date = today
        emit subscription_event COMPLETED
    write audit_log
  COMMIT
```

Row-level lock on the subscription + the unique `(subscription_id, delivery_date,
time_slot)` constraint together make concurrent marking by two staff safe: the
second transaction either no-ops (already terminal) or serializes behind the
lock. (Edge case Q11.3)

### 6.3 Reversal

```
reverse_delivery(delivery_id, reason):
  BEGIN
    lock subscription FOR UPDATE
    assert delivery.status == DELIVERED and not delivery.reversed
    subscription.meals_consumed -= delivery.meals_deducted
    delivery.reversed = true; reversal_reason = reason; reversed_by/at set
    delivery.status = FAILED           # or a dedicated REVERSED display state
    if subscription.status == COMPLETED and subscription.meals_remaining > 0
       and today <= subscription.expected_end_date:
        subscription.status = ACTIVE
    write audit_log (DELIVERY_REVERSED)
  COMMIT
```

---

## 7. Payments & Refunds

- Subscription owes `snapshot_final_price`. (BR-8)
- Multiple installment payments allowed; each is a `payments` row. (Q7.2)
- `payment_status` / `outstanding_amount` derived per BR-25/BR-26 — computed in a
  service function and exposed on subscription read models; never stored stale.
- Refunds are ADMIN-entered with amount, date, reason, method, optional
  reference. No automatic proration. A **suggested** prorated figure
  (`snapshot_final_price × meals_remaining / meals_allocated`) may be shown in the
  UI as guidance only. (Q7.6)
- Payment does not gate deliveries; the UI shows an outstanding-dues badge.
  (BR-27)
- Tax fields (`base_price`, `tax_amount`, `final_price`) exist on package and
  snapshot now; GST percentages are not hardcoded and can stay zero in v1.
  (Q7.8)
- PDF invoices deferred; a plain printable payment record is a later add. (Q7.7)

---

## 8. REST API

Base path `/api/v1`. JSON. Bearer auth on everything except `/auth/login` and
`/health`. Standard error envelope:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": [...] },
  "warnings": [ { "code": "POSSIBLE_DUPLICATE", "message": "..." } ] }
```

Pagination: `?page`, `?page_size` (default 25, max 100), responses carry
`{ items, total, page, page_size }`. List filtering/sorting via query params.

### 8.1 Endpoint summary

| Method & path | Purpose | Min role |
|---|---|---|
| `POST /auth/login` | email+password → tokens | – |
| `POST /auth/refresh` | rotate tokens | – |
| `POST /auth/logout` | revoke refresh token | STAFF |
| `GET /auth/me` | current user | STAFF |
| `GET /users` · `POST /users` | list / create users | ADMIN |
| `GET /users/{id}` · `PATCH /users/{id}` | view / update | ADMIN |
| `POST /users/{id}/deactivate` | disable login | ADMIN |
| `GET /customers` | search (`q`, `phone`, `code`, `is_active`) + paginate | STAFF |
| `POST /customers` | create (+ first address) | STAFF |
| `GET /customers/{id}` | detail incl. subscriptions summary | STAFF |
| `PATCH /customers/{id}` | update | STAFF |
| `POST /customers/{id}/deactivate` · `/reactivate` | soft-delete toggle | ADMIN |
| `GET/POST /customers/{id}/addresses` | list / add | STAFF |
| `PATCH/DELETE /customers/{id}/addresses/{aid}` | update / deactivate | STAFF |
| `GET /packages` | list (`status` filter) | STAFF |
| `POST /packages` | create | ADMIN |
| `GET /packages/{id}` | detail | STAFF |
| `PATCH /packages/{id}` | edit (name/desc/price/meals/validity/tax) | ADMIN |
| `POST /packages/{id}/activate` · `/deactivate` | status | ADMIN |
| `DELETE /packages/{id}` | hard-delete (only if unused) | ADMIN |
| `GET /subscriptions` | list (`status`, `customer_id`, `expiring=true`, `dues=true`) | STAFF |
| `POST /subscriptions` | create (snapshot happens here) | STAFF |
| `GET /subscriptions/{id}` | detail incl. derived payment status, meals, events | STAFF |
| `PATCH /subscriptions/{id}` | edit notes / address / schedule / slot | STAFF |
| `POST /subscriptions/{id}/pause` · `/resume` | pause / resume (+reason) | STAFF |
| `POST /subscriptions/{id}/extend` | extend (+days/date +reason) | ADMIN |
| `POST /subscriptions/{id}/cancel` | cancel (+reason) | ADMIN |
| `POST /subscriptions/{id}/renew` | create linked PENDING/ACTIVE subscription | STAFF |
| `POST /subscriptions/{id}/meal-adjustments` | adjust balance (+qty +reason) | ADMIN |
| `GET /subscriptions/{id}/deliveries` · `/payments` · `/events` | sub-collections | STAFF |
| `POST /subscriptions/{id}/skips` · `DELETE .../skips/{sid}` | planned skips | STAFF |
| `GET /deliveries?date=YYYY-MM-DD` | daily list (also `area`, `slot`, `status`) | STAFF |
| `POST /deliveries/generate` | body `{ "date": "..." }` — idempotent | STAFF |
| `PATCH /deliveries/{id}` | set status / slot / notes | STAFF |
| `POST /deliveries/{id}/reverse` | reverse a DELIVERED (+reason) | STAFF |
| `POST /subscriptions/{id}/payments` | record payment | STAFF |
| `GET /payments` · `GET /payments/{id}` | list / detail | STAFF |
| `POST /subscriptions/{id}/refunds` | issue refund | ADMIN |
| `GET/POST/DELETE /holidays` | closed-day calendar | ADMIN (write) / STAFF (read) |
| `GET /dashboard/summary` | counts (see §9) | STAFF |
| `GET /exports/{customers\|subscriptions\|payments\|deliveries}.csv` | CSV export | STAFF |
| `POST /imports/customers` | multipart CSV upload → validation report → commit | ADMIN |
| `GET /imports/{id}` | import job status / errors | ADMIN |
| `GET /settings` · `PATCH /settings` | thresholds / code formats | STAFF (read) / ADMIN (write) |
| `GET /audit-logs` | filter by entity / actor / date | ADMIN |
| `GET /health` | liveness/readiness | – |

### 8.2 Create-subscription request (shape)

```json
POST /api/v1/subscriptions
{
  "customer_id": 42,
  "package_id": 3,
  "start_date": "2026-09-15",
  "delivery_frequency": "SPECIFIC_WEEKDAYS",
  "delivery_weekdays": [1, 3, 5],
  "meals_per_delivery": 1,
  "delivery_time_slot": "MORNING",
  "delivery_address_id": 88,
  "dietary_preference_override": null,
  "subscription_notes": "Gate code 4471"
}
```

Server: validates package is `ACTIVE`, customer is active, no existing `ACTIVE`
subscription (else new one is `PENDING`), computes `original_end_date`,
snapshots package + address + dietary, assigns `subscription_code` and
`subscription_number`, writes `subscription_event CREATED`.

---

## 9. Dashboard & Monitoring

`GET /dashboard/summary` returns (Q9.4 — deliberately minimal):

| Field | Definition |
|---|---|
| `active_subscriptions` | count `status = ACTIVE` |
| `todays_meals_planned` | Σ `meal_quantity` of today's `SCHEDULED`/interim deliveries |
| `delivered_today` | count today's `DELIVERED` |
| `expiring_soon` | subscriptions where `expected_end_date - today ≤ expiry_days_threshold` **OR** `meals_remaining ≤ expiry_meals_threshold` (Q9.1) |
| `outstanding_dues_total` | Σ `outstanding_amount` over non-terminal subscriptions |

Monitoring lists (each a filtered `GET /subscriptions`): Active, Completed,
Expired, Expiring-soon, Dues. Plus "Today's deliveries" (`GET /deliveries`).

Screens in v1 (Q9.2): Login · Dashboard · Customer list · Create customer ·
Customer detail · Package list · Create/edit package · Subscription list ·
Subscription detail · Create subscription · Today's deliveries · Active /
Completed / Expired / Expiring-soon lists · Dues & payments · Users & settings.

CSV export (Q9.3): customers, subscriptions, payments, daily deliveries. UTF-8,
comma-separated, ISO dates, amounts as plain decimals.

---

## 10. CSV Import (customers)

ADMIN-only, two-phase:

1. **Upload & validate** — `POST /imports/customers` with the file. Server parses,
   validates every row (required fields, phone/email uniqueness, address
   structure, enum values), and returns a report: `{ total, valid, invalid,
   errors: [{ row, field, message }] }`. Nothing is written yet.
2. **Commit** — `POST /imports/{id}/commit` writes valid rows in a single
   transaction (or row-batched with a summary). Optional columns allow seeding a
   *current* subscription per customer where the data is present.

Expected columns (documented template): `name, phone, email, dietary_preference,
allergies, notes, address_line, area, city, pincode, landmark, delivery_notes`
and optionally `package_code, subscription_start_date, delivery_frequency,
delivery_weekdays, meals_per_delivery, time_slot`.

---

## 11. Deployment (AWS, `ap-south-1`)

| Concern | Choice |
|---|---|
| Database | **RDS for PostgreSQL 16**, single-AZ for v1 with automated daily backups + point-in-time recovery (7–14 day retention); Multi-AZ is a flip when needed (Q10.3) |
| Backend | Containerized FastAPI on **ECS Fargate** behind an **ALB** (or **App Runner** for a simpler start); image in **ECR** |
| Daily job | **EventBridge Scheduler** → one-off ECS task (or Lambda) running the expiry/activation sweep |
| Frontend | Next.js on **AWS Amplify Hosting** (SSR-capable) or ECS Fargate + CloudFront; static assets via CloudFront |
| Secrets | **AWS Secrets Manager** (DB creds, JWT signing key) / SSM Parameter Store |
| TLS | **ACM** certificates; HTTP→HTTPS redirect; HSTS |
| Networking | VPC with public subnets (ALB) and private subnets (ECS tasks, RDS); RDS not publicly accessible; security groups least-privilege |
| Object storage | **S3** for CSV import uploads / export staging (lifecycle-expired) |
| Logs & metrics | **CloudWatch** logs (structured JSON) + alarms on 5xx rate, latency, DB CPU/connections |
| IaC | **Terraform** (or AWS CDK) — environments `dev` and `prod` |
| CI/CD | GitHub Actions: lint → test → build image → push ECR → deploy; Alembic migrations run as a pre-deploy step |

Environments: `dev` (single small instance, may share one RDS) and `prod`.
Config via environment variables + Secrets Manager; no secrets in the repo.

---

## 12. Testing Strategy

Framework: **pytest**. Test DB: a real PostgreSQL (docker / testcontainers) with
per-test transaction rollback; factory fixtures for users, customers, packages,
subscriptions.

Layers:

- **Unit** — pure business functions: expiry date math, `meals_remaining`,
  `payment_status`/`outstanding_amount`, status-transition guards, `due_on`
  schedule logic, code generation.
- **Integration** — API endpoints against the test DB, including auth/RBAC per
  route, concurrency guard on delivery marking (parallel transactions), and the
  idempotency of delivery generation.
- **Regression** — one test per edge case in §13.

Priority order for first tests (Q1.7):

1. Package business rules (bounds, used-package immutability, snapshot on assign)
2. Subscription creation (snapshot correctness, one-ACTIVE rule, PENDING queueing)
3. Expiry calculations (calendar days, Tuesday/holiday do not extend, pause
   extension, admin extension)
4. Meal deduction (DELIVERED only, multi-meal deliveries, COMPLETED at zero)
5. Delivery reversal (exact restore, COMPLETED→ACTIVE rollback, audit written)
6. Payment calculations (installments, partial/paid/unpaid/refunded, outstanding)

Target: CI green on every PR; coverage tracked (no hard gate in v1, but service
layer expected ≥ 85%).

---

## 13. Edge Cases & Handling

| # | Case (Q11.3) | Handling |
|---|---|---|
| 1 | Customer pauses subscription | `PAUSED`; deliveries blocked; on resume `expected_end_date += paused_days`; event + audit (BR-22) |
| 2 | Address changes mid-subscription | New/updated `customer_addresses` row; subscription keeps its `snapshot_delivery_address` unless explicitly edited; edit is audited |
| 3 | Customer skips several days | `planned_skips` range; generation skips those dates; no meal impact |
| 4 | Meal marked delivered by mistake | Reverse with reason; exact `meals_deducted` restored; `COMPLETED`→`ACTIVE` if applicable; audit (BR-30) |
| 5 | Two staff mark the same delivery at once | `SELECT … FOR UPDATE` on subscription + unique `(subscription_id, delivery_date, time_slot)`; second txn no-ops or serializes (§6.2) |
| 6 | Subscription expires with meals left | `EXPIRED`, meals forfeited; only an ADMIN extension revives it (BR-20/21) |
| 7 | Customer renews before expiry | New `PENDING` subscription, `previous_subscription_id` set, activates when current closes; balances not combined (BR-34) |
| 8 | Package changed after purchase | Existing subscriptions read their snapshot; only new subscriptions see new values (BR-5) |
| 9 | Multiple meals in one delivery | `meal_quantity > 1`; balance decremented by that amount (BR-16) |
| 10 | Package starts in the future | `start_date` future-dated; subscription `PENDING`/`ACTIVE` per one-ACTIVE rule; generation only from `start_date` |
| 11 | Goodwill meal credit | ADMIN `meal_adjustment` (+qty, reason); audited (BR-18) |
| 12 | Refund issued | ADMIN `refunds` row; `payment_status` → `REFUNDED`; audited; no auto-proration (§7) |
| 13 | Outstanding payment but meals continue | Allowed by design; dues badge shown (BR-27) |
| 14 | Closed Tuesdays | `closed_weekday` config; no generation/recording; validity still counts the day (BR-28, BR-10) |
| 15 | Special business holidays | `holidays` table; same treatment as Tuesday (BR-28) |
| 16 | Customer deactivated, history kept | Soft delete; hidden from active lists; history fully readable (BR-3) |
| 17 | Same customer entered twice | Hard unique on phone/email; soft duplicate warning on similar name+phone (§3.3) |

---

## 14. Non-Functional Requirements

| Area | Target |
|---|---|
| Scale | up to ~10,000 customers, thousands of subscriptions, ~1,000 deliveries/day; 5–20 users, 1–10 concurrent — nothing hardcoded to these numbers (Q2.5, Q10.1) |
| Performance | p95 < 300 ms for list/detail endpoints at target scale; daily generation for 1,000 deliveries < 30 s |
| Availability | single region `ap-south-1`; RDS automated backups + PITR; Multi-AZ optional |
| Security | HTTPS only; Argon2id passwords; short-lived JWT + rotating refresh; RBAC enforced server-side; auth rate-limiting; least-privilege IAM & security groups; no PII in logs; audit log immutable (§5) |
| Backups | RDS daily automated + PITR (7–14 days); tested restore procedure documented (Q10.3) |
| Observability | structured JSON logs with request IDs; CloudWatch metrics + alarms (5xx, latency, DB connections/CPU) |
| Devices | responsive web; desktop-first, tablet/mobile usable (Q10.4) |
| Offline | not supported in v1 (Q10.5) |
| Localization | single locale `en-IN`; currency INR; timezone `Asia/Kolkata` (business `DATE`s interpreted in IST; timestamps stored UTC) (Q10.2) |

### 14.1 Branding & UI direction (Q1.3, Q10.6)

- Name: **HealthX**.
- Palette: white, off-white, black, slate. No gradients, no glassmorphism, no
  purple/blue "AI" palette.
- Minimal, professional, restrained, operational. Very restrained rounded
  corners. No oversized cards, decorative charts, or unnecessary animation.
- Dense, legible tables; clear primary actions; fast keyboard-friendly search.

---

## 15. Repository Structure (proposed)

```
subscription-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── core/                   # config, security, db session, deps
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── api/v1/routers/         # HTTP endpoints
│   │   ├── services/               # business rules (transactional)
│   │   ├── repositories/           # query helpers
│   │   └── workers/                # scheduled jobs (expiry/activation sweep)
│   ├── alembic/                    # migrations
│   ├── tests/                      # pytest (unit / integration / regression)
│   └── pyproject.toml
├── frontend/
│   ├── app/                        # Next.js App Router
│   ├── components/
│   ├── lib/                        # API client, auth, formatting
│   └── package.json
├── infra/                          # Terraform (dev / prod)
├── progress/                       # planning docs (this file, questionnaire, …)
└── README.md
```

The current root `tools.py` and `src/subscription_tracker/` stub are removed once
`backend/` lands.

---

## 16. Milestones (Q11.2)

No hard deadline. Ordered delivery:

| Milestone | Contents |
|---|---|
| **M1 — Foundation** | Repo restructure, PostgreSQL + Alembic, `users`, auth (login/refresh/RBAC), audit-log infra, settings, health check, CI |
| **M2 — Customers & Packages** | Customer CRUD + soft delete + addresses + search + duplicate warning; package CRUD + activate/deactivate + hard-delete-if-unused; bounds validation |
| **M3 — Subscriptions** | Create + snapshot; one-ACTIVE / PENDING queueing; expiry math; pause/resume; extend; cancel; renew; meal adjustments; subscription events; hybrid status recompute |
| **M4 — Deliveries** | Frequency model; daily generation (Tuesday/holiday/skip aware); outcome recording with concurrency guard; reversal; holiday calendar; planned skips |
| **M5 — Payments** | Installment payments; derived payment status / outstanding; refunds; dues list |
| **M6 — Dashboard, reporting, deploy** | Dashboard summary; monitoring lists; CSV export; CSV customer import; expiring-soon alerts; daily scheduled job; AWS deploy (Terraform, RDS, ECS/Amplify, backups, alarms); test hardening |

---

## 17. Open Items / v2 Candidates

- 2FA for staff logins; configurable password policy
- Automated expiry / dues / renewal notifications (WhatsApp / SMS / email)
- Customer-facing portal
- Delivery route planning, area zoning, driver assignment
- PDF invoices / receipts
- Suggested-refund proration surfaced in the cancel flow
- Analytics / BI / churn reporting
- Multi-AZ RDS + read replica if load grows
- Configurable "expiring soon" thresholds exposed in the UI (backend already
  reads them from `settings`)
