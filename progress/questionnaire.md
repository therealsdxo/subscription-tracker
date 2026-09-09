# HealthX — Requirements Questionnaire (Phase Zero)

Prepared after reviewing `project.md`. The goal is to close every knowledge gap
before any code is written. Please answer inline under each question (a short
answer is fine). Where I have a recommendation as the engineer, I've marked it
**[suggest: …]** — feel free to just confirm or override.

I've grouped questions by area. Section **0** lists contradictions in the current
`project.md` that need a decision either way.

---

## 0. Inconsistencies in project.md to resolve

0.1 Section 1 lists the customer record with subscription fields baked in
(`customer_package`, `customer_numberOfMeals`, `customer_mealsLeft`,
`customer_packageStartDate`, `customer_expectedEndDate`, `payment_status`,
`subscription_status`, `resubscribe_number`). But `resubscribe_number` and the
"Renewed subscriptions" monitoring imply a customer can have **many**
subscriptions over time. Do you want:

## Answer:
Use a normalized model:
Customer 1 → Many Subscriptions
Customer information stays on the customer record. Package, meal balance, payment status, subscription dates, and subscription status belong to the subscription. This also allows full renewal history.


0.2 `BL-04` says a user can delete a customer, but `BL-17` requires historical
subscription records to stay intact. If a customer with past subscriptions is
deleted, what should happen — block it, soft‑delete (hide but keep records), or
hard‑delete and cascade everything?

## Answer:
Use soft delete.
Deleting a customer should hide/deactivate them from normal operations but retain all historical subscriptions, deliveries, and payments.

0.3 `BL-07` and `BL-12` are identical ("Meals Remaining = Total Allocated −
Consumed"). Confirm that's just a duplicate and there's no second rule intended.

## Answer:
Yes. Treat this as a duplicate rule. Keep only:
Meals Remaining = Total Meals Allocated - Meals Consumed

0.4 Section 1 customer fields list `customer_phoneNo` but not email; `BL-01` makes
**email** mandatory. Which contact fields are truly required vs optional?

## Answer:
Required:
- Name
- Phone number
- Delivery address
Optional:
- Email
Email should not be mandatory for v1.


0.5 The outlet is closed Tuesdays and no meals are delivered then, but validity is
described in **calendar days** ("start_date + validity_days"). Do Tuesdays (and
any holidays) count toward the validity window, or should expiry be extended to
skip non‑delivery days? See Q4.3.

## Answer:
Use calendar-day validity.
Tuesdays and holidays still count toward package validity. A closed delivery day should not automatically extend the subscription.

---

## 1. Tech stack & architecture

1.1 The repo is a Python 3.13 / `uv` project and currently just a CLI stub with
in‑memory dicts (`tools.py`). `project.md` calls this a "web based project."
What are we actually building for v1:
- (a) REST/JSON API backend only
- (b) API backend + separate web frontend (SPA)
- (c) server‑rendered web app (templates)
- (d) internal admin UI on top of a framework's admin (e.g. Django admin)?
**[suggest: c or d for an internal tool — fastest path to a usable system]**

## Answer:
(b) API backend + separate web frontend
Architecture:
Next.js Web App → FastAPI API → PostgreSQL

1.2 Backend framework preference? (FastAPI, Django, Flask, other)
**[suggest: Django if we want batteries‑included admin/auth/ORM; FastAPI +
SQLModel if we want an API‑first service]**

## Answer:
FastAPI

1.3 If there's a frontend (1.1b/1.1c), any framework/styling preference
(React, HTMX, plain templates, Tailwind, Bootstrap)?

## Answer:
Use:
- Next.js
- React
- TypeScript
- Tailwind CSS
UI requirements:
- Minimal
- White
- Off-white
- Black
- Slate
- Very restrained rounded corners
- No gradients
- No glassmorphism
- No generic AI dashboard aesthetic

1.4 Database engine? (PostgreSQL, SQLite, MySQL, MongoDB)
**[suggest: PostgreSQL for prod, SQLite for local dev]**

## Answer:
PostgreSQL for both development and production.

1.5 Where will this be deployed / hosted? (local machine, a VPS, a PaaS like
Render/Railway/Fly, cloud, on‑prem at the outlet)

## Answer:
I want to host it using AWS 

1.6 Is the in‑memory `tools.py` code meant to be kept/extended, or replaced with
a proper persistence layer? **[suggest: replace]**

## Answer:
Replace it with a proper persistence layer.

1.7 Do you want automated tests from the start? Which framework — `pytest`?

## Answer:
Yes.
Use:
pytest
Tests should start with:
- Package business rules
- Subscription creation
- Expiry calculations
- Meal deduction
- Delivery reversal
- Payment calculations

---

## 2. Users, roles & authentication

2.1 Who uses this system — only internal staff, or do customers log in too?
**[suggest: internal staff only for v1]**

## Answer:
Internal staff only for v1.


2.2 What roles exist? e.g. Admin (manage packages, users, pricing) vs Staff
(manage customers, record deliveries/payments). Or is everyone equal for v1?

## Answer:
Use two roles initially:
ADMIN
Can manage everything.
STAFF
Handles everyday operations.

2.3 What can a non‑admin **not** do? (create/deactivate packages? change pricing?
delete customers? issue refunds?)

2.4 How do users authenticate — username+password, email+password, SSO/Google?
Any password policy / 2FA requirement?

2.5 How many staff users total, and roughly how many use it concurrently?

2.6 Do you need an **audit log** (who created/updated/deleted what, and when)?
**[suggest: yes — at least for deliveries, payments, package changes, meal
adjustments]**

---

## 3. Customer

3.1 `customer_id` — system‑generated (e.g. `CUST-00001`) or entered by staff?
Any required format?

3.2 Which customer fields are **required** vs optional:
name, phone, email, address, dietary preference, delivery instructions?

3.3 Must phone and/or email be **unique**? Should the system warn on likely
duplicate customers (same phone/name)?

3.4 Address: one address per customer, or separate billing vs delivery address?
Free‑text or structured (line1, area, city, pincode, landmark)? Do you need
pincode/area for delivery zoning later?

3.5 Can a customer's delivery address differ **per subscription**, or is it always
the customer's current address?

3.6 **Dietary preference** — does it belong to the customer or the subscription?
Is it a fixed list (Veg / Non‑Veg / Vegan / Jain / Eggetarian) or free text?
Do you need to record allergies separately?

3.7 Any GDPR‑style / privacy requirements for storing customer contact data?

---

## 4. Packages

4.1 `package_id` — system‑generated or manual?

4.2 Field types: are `number_of_meals` and `validity_days` always whole numbers?
Is price always integer INR, or can it have paise? Currency always INR?

4.3 **Validity window definition** (critical): is `validity_days` counted as
calendar days from start date, or as delivery days (excluding Tuesdays/holidays)?
Example: 25‑meal / 50‑day package starting Mon 01 Sep 2026 — what exact date does
it expire? **[suggest: calendar days, expiry = start + validity_days, inclusive
of start date; Tuesdays don't extend it]**

4.4 When an authorized user edits a package (price, meals, validity, name),
should existing **active** subscriptions be completely unaffected (per BL‑17)?
Confirm: yes, edits only apply to *new* subscriptions from that point.

4.5 Can a package be **hard‑deleted** if it has never been used in any
subscription? (BL‑16 only covers used packages → inactive.)

4.6 Are `package_description` and `package_status` required on creation? Default
status = ACTIVE?

4.7 Any minimum/maximum bounds you want enforced (e.g. meals 1–500, validity
1–365 days, price ≥ 0)?

---

## 5. Subscriptions

5.1 Can a customer have **more than one ACTIVE subscription at the same time**, or
strictly one at a time? **[suggest: one active at a time for v1]**

5.2 `subscription_id` format — system‑generated?

5.3 `start_date` — can staff **back‑date** it (subscription started last week) or
**future‑date** it (starts next Monday)? Any limits?

5.4 What if `start_date` falls on a Tuesday — allowed, auto‑shifted to next day,
or blocked?

5.5 Exactly which package fields are **snapshotted** onto the subscription at
creation (BL‑17): name, meals, validity_days, price — anything else?

5.6 Besides the snapshot, does the subscription store: delivery frequency,
dietary preference, delivery address, delivery time slot, notes?

5.7 **Status computation** — is `subscription_status` a stored field updated by a
scheduled job (e.g. nightly), or computed live whenever a record is viewed?
**[suggest: computed live for correctness, plus a nightly job to snapshot for
reporting/alerts]**

5.8 `COMPLETED` triggers when `meals_remaining = 0` even if before the expiry
date — confirm. And once COMPLETED, is the subscription closed (no more
deliveries) until a renewal?

5.9 When a subscription `EXPIRES` with meals left, those meals are forfeited
unless an authorized user extends it. Who can extend, and how — push the expiry
date out by N days? Is there any log/reason required?

5.10 **PAUSED** — who can pause, why (customer travelling, etc.), and does a
pause **extend the expiry date** by the paused duration? **[suggest: yes, pausing
extends expiry by the pause length]**

5.11 **CANCELLED** — who can cancel, and does cancellation trigger a refund
calculation (see Q7.6)? Is a reason required?

5.12 Can staff **manually adjust `meals_remaining`** (goodwill credit, comp for a
bad meal, correcting a mistake)? If yes, should it require a reason + be audited?
**[suggest: yes, with mandatory reason]**

---

## 6. Deliveries & meal consumption

6.1 **Delivery frequency** is mentioned repeatedly but never defined. How is it
expressed per customer/subscription — e.g. "1 meal/day", "2 meals/day",
"specific weekdays", "every other day", "on-demand"? Give the exact set of
options you want.

6.2 Is a "delivery" always exactly **one meal** (BL‑13), or can one delivery
event cover multiple meals (e.g. deliver 2 meals in one drop)?

6.3 How are deliveries recorded — staff manually mark each delivery day by day,
a bulk "mark today's deliveries" screen, or an auto‑generated daily delivery
list that staff then confirm/adjust? **[suggest: auto‑generate the day's
expected deliveries, staff confirm/override]**

6.4 Delivery outcome values and who sets them: `DELIVERED`, `SKIPPED`,
`CANCELLED`, `FAILED`, `NOT_DELIVERED` (from BL‑14). Any others (e.g.
`RESCHEDULED`)? Which of these are customer‑requested vs operational?

6.5 Only `DELIVERED` decrements the meal balance — confirm. Skipped/failed/etc.
never consume a meal and never extend expiry (unless manually done)?

6.6 Can a recorded delivery be **edited or reversed** later (marked delivered by
mistake)? Should that restore the meal? **[suggest: yes, with audit]**

6.7 Should the system **block** creating/recording a delivery on a **Tuesday**?
Are there other closed days / holidays, and do you need a holiday calendar you
can maintain?

6.8 Can a delivery be recorded against an `EXPIRED`, `COMPLETED`, `PAUSED`, or
`CANCELLED` subscription? **[suggest: no — hard block, this is a core problem the
system exists to prevent]**

6.9 Do customers request **skip days in advance** (e.g. "no meals next Thu–Fri"),
and should the system store planned skips?

6.10 Do you need **delivery scheduling / route planning** in v1 (grouping by
area, delivery sequence, driver assignment), or just per‑customer address + a
daily list? **[suggest: just the daily list for v1]**

6.11 Delivery **time slots** (morning/evening) — track them?

---

## 7. Payments

7.1 Is a payment tied to a **subscription** (one subscription → its payments)?
Confirm.

7.2 Can a subscription be paid in **multiple installments** (record several
payments that sum to the package price), or always a single payment?
**[suggest: support multiple — needed for PARTIALLY_PAID]**

7.3 What determines `payment_status`:
- `UNPAID` = 0 paid, `PARTIALLY_PAID` = 0 < paid < price, `PAID` = paid ≥ price,
  `REFUNDED` = money returned?
Confirm this mapping and how `outstanding_amount` is derived.

7.4 Do you record **payment method** (Cash / UPI / Card / Bank transfer) and a
reference number?

7.5 Does an `UNPAID` or `PARTIALLY_PAID` status **block** activating the
subscription or recording deliveries, or is delivery allowed regardless (payment
tracked separately)? **[suggest: allow delivery, just flag the dues]**

7.6 **Refunds** — when a subscription is cancelled with meals remaining, is the
refund: full, nothing, or pro‑rated (`price × meals_remaining / total_meals`)?
Who can issue a refund? Do you need to store refund amount + date + reason?

7.7 Do you need **invoices / receipts** (PDF or printable) in v1?
**[suggest: defer]**

7.8 Any taxes/GST to record on the package price?

---

## 8. Renewals / resubscription

8.1 A renewal creates a **new** subscription record linked to the customer and
increments `resubscribe_number` — confirm (vs. resetting the same record).

8.2 Can a customer renew **before** the current subscription ends? If so, does the
new subscription start immediately (stacking meals) or queue to start after the
current one ends? **[suggest: queue to start at current expiry/completion]**

8.3 Can the renewal use a **different package** than the previous one?

8.4 Is `resubscribe_number` a per‑customer counter (1st, 2nd, 3rd subscription)?
Does the very first subscription count as 0 or 1?

8.5 Do you want to carry forward unused meals from the previous subscription on
renewal? **[suggest: no]**

---

## 9. Monitoring, dashboards & reporting (v1)

9.1 "Subscriptions approaching expiry" — define the threshold: X days before
expiry (what X?), or Y meals remaining (what Y?), or both?

9.2 List the exact **screens/lists** you need in v1. My proposed minimum:
- Customer list + search (by name, number, id)
- Customer detail (contact + current + past subscriptions)
- Subscription detail (meals allocated/consumed/remaining, dates, status, payment)
- Today's delivery list (mark delivered/skipped/etc.)
- Active subscriptions / Completed / Expired / Approaching‑expiry lists
- Dues list (unpaid / partially paid)
- Package management (create/edit/activate/deactivate)
Add/remove anything.

9.3 Do you need **CSV/Excel export** of any of these lists in v1?

9.4 Any single "dashboard" with counts (active customers, meals to deliver today,
dues total, expiring this week)? **[suggest: yes, small and simple]**

---

## 10. Non‑functional & operational

10.1 Expected scale: how many customers total (now / in 1 year)? Deliveries per
day?

10.2 Timezone — everything in IST (Asia/Kolkata)? Confirm.

10.3 Do you need **data backups** / is the hosting provider handling that?

10.4 Primary device usage — desktop browser at the outlet, or also mobile/tablet
for delivery staff in the field?

10.5 Does the app need to work **offline** at all (spotty connectivity for
delivery staff)? **[suggest: no for v1]**

10.6 Any branding (name shown as "HealthX", logo, colors)?

10.7 Do you need **bulk import** of existing customers (from a spreadsheet) to
get started?

10.8 Explicitly **out of scope for v1** (please confirm): WhatsApp/SMS/email
notifications, automated expiry alerts, payment reminders, customer‑facing
portal, analytics/BI, route optimization. Anything to pull *into* v1 from this
list?

---

## 11. Anything else

11.1 Is there an existing spreadsheet/tool this replaces? Can you share its
columns — it's the fastest way to catch missing fields.

11.2 Any hard deadline or milestone for v1?

11.3 Any rule or edge case you already know is tricky that I haven't asked about?
