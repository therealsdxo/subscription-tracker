# Goals

1. You're a senior backend engineer continuing the HealthX build. Work strictly
   from `project.md`, `progress/questionnaire.md`, `progress/tech_doc.md`, and the
   foundation delivered in `progress/phase_two.md` (Milestone 1). Follow the
   patterns already established in `backend/` — routers → services (transactional,
   own all invariants) → repositories → models; Pydantic schemas per resource;
   `audit_service.record()` for sensitive actions; ADMIN/STAFF guards from
   `app.core.deps`.

2. Deliver **Milestone 2 — Customers & Packages** (`tech_doc.md` §16). This is the
   first domain slice. No subscriptions, deliveries, or payments yet — but the
   models and code must not block them (§3.1 relationships).

3. Code generation helper (`tech_doc.md` §3.2):
   - Add a service that produces the next human-readable code from a per-entity
     Postgres sequence, using prefix + zero-pad width read from the `settings`
     table (`customer_code_prefix`/`_width`, `package_code_prefix`/`_width`).
     `subscription_code_*` is seeded already but unused this phase.
   - Codes are unique, immutable, and shown in the UI and exports.

4. Packages (`tech_doc.md` §3.3, §4.2 BR-4…BR-7, §8):
   - Migration for `packages`: `id`, `package_code` (unique), `name`,
     `description` (nullable), `number_of_meals` (int, **1–500**), `validity_days`
     (int, **1–730**), `base_price` `NUMERIC(10,2)` **≥ 0**, `tax_amount`
     `NUMERIC(10,2)` default 0, `final_price` `NUMERIC(10,2)` = base + tax
     (stored, validated), `status` enum `package_status` (`ACTIVE` | `INACTIVE`,
     default `ACTIVE`), timestamps + `created_by`/`updated_by`.
   - Endpoints: `GET /packages` (filter `status`), `POST /packages` (ADMIN),
     `GET /packages/{id}`, `PATCH /packages/{id}` (ADMIN — name/description/
     price/meals/validity/tax), `POST /packages/{id}/activate` · `/deactivate`
     (ADMIN), `DELETE /packages/{id}` (ADMIN).
   - Rules:
     - Editing a package must **never** touch existing subscriptions — nothing to
       cascade yet, but document that snapshotting happens at subscription
       creation (BR-5). No "apply to existing" behaviour.
     - `DELETE` succeeds **only if the package has never been used by any
       subscription** (BR-6). Until the `subscriptions` table exists, treat "used"
       as always false — but implement the check as a service call
       (`is_package_referenced()`) that Milestone 3 fills in, so the guard is
       already wired.
     - A used package can only be `INACTIVE`; `INACTIVE` packages cannot be
       assigned to new subscriptions (enforced in M3).
     - Bounds validation in the Pydantic schema **and** as DB check constraints.
   - Audit: `PACKAGE_CREATED`, `PACKAGE_UPDATED`, `PACKAGE_ACTIVATED`,
     `PACKAGE_DEACTIVATED`, `PACKAGE_DELETED` (`tech_doc.md` §2.6).

5. Customers (`tech_doc.md` §3.1, §3.3, §4.1 BR-1…BR-3, §8):
   - Migration for `customers`: `id`, `customer_code` (unique), `name`, `phone`
     (**unique**, required), `email` `citext` (nullable, **unique when present**),
     `default_dietary_preference` enum `dietary_pref`
     (`VEGETARIAN`|`NON_VEGETARIAN`|`EGGETARIAN`|`VEGAN`|`JAIN`|`OTHER`, nullable),
     `dietary_notes` (nullable), `allergies` (nullable — separate field),
     `notes` (nullable), `is_active` (bool, default true — soft-delete flag),
     `deactivated_at`/`deactivated_by`/`deactivation_reason`, timestamps +
     `created_by`/`updated_by`.
   - Migration for `customer_addresses`: `id`, `customer_id` FK (on delete
     restrict), `label`, `address_line`, `area`, `city`, `pincode`, `landmark`
     (nullable), `delivery_notes` (nullable), `is_primary` (bool — exactly one
     primary per customer via partial unique index), `is_active` (bool, default
     true), timestamps.
   - Endpoints:
     - `GET /customers` — search by `q` (name), `phone`, `code`; filter
       `is_active`; paginated (`page`, `page_size`, envelope from §8).
     - `POST /customers` — create; **requires name, phone, and at least one
       address** (BR-2). Email optional.
     - `GET /customers/{id}` — detail (contact + addresses; subscriptions summary
       added in M3).
     - `PATCH /customers/{id}` — update contact / dietary / notes.
     - `POST /customers/{id}/deactivate` · `/reactivate` (ADMIN) — soft delete;
       deactivate requires a reason; audited. History is retained (nothing to
       retain yet, but never hard-delete).
     - `GET/POST /customers/{id}/addresses`, `PATCH/DELETE
       /customers/{id}/addresses/{aid}` (DELETE = deactivate the address).
   - Rules:
     - **Duplicate warning** (`tech_doc.md` §3.3, §13 case 17): on create/update,
       if an active customer has a similar `name` **and** same/similar `phone`,
       return a `warnings` array in the response envelope and still proceed. Exact
       `phone`/`email` collisions are hard 409 unique-constraint errors
       (`code` `PHONE_TAKEN` / `EMAIL_TAKEN`).
     - Deleting a customer is **always** soft (`is_active = false`) — `BL-04` is
       overridden by Q0.2. There is no hard-delete endpoint.
   - Audit: `CUSTOMER_CREATED`, `CUSTOMER_UPDATED`, `CUSTOMER_DEACTIVATED`,
     `CUSTOMER_REACTIVATED`, `CUSTOMER_ADDRESS_ADDED`, `CUSTOMER_ADDRESS_UPDATED`,
     `CUSTOMER_ADDRESS_REMOVED`.

6. Permissions — apply the `tech_doc.md` §5.2 matrix:
   - STAFF: create/update customers, manage addresses, search, view packages.
   - ADMIN only: deactivate/reactivate customers; all package
     create/edit/activate/deactivate/delete.

7. Models: add `Customer`, `CustomerAddress`, `Package` and their enums to
   `app/models/__init__.py` so Alembic and tests see them. Keep the FK to
   `subscriptions` out for now; add relationship stubs only where harmless.

8. Migrations:
   - One Alembic revision per logical group is fine (`0002_packages`,
     `0003_customers`) or a single `0002_customers_and_packages` — your call, but
     each must `upgrade` **and** `downgrade` cleanly on a clean database.
   - Native enums (`package_status`, `dietary_pref`): create/drop explicitly like
     `0001` did for `user_role` (autogenerate is unreliable for enums).
   - Check constraints for the numeric bounds.

9. Tests (`pytest`, extend `tests/`):
   - Package: bounds rejected (meals 0 / 501, validity 0 / 731, price < 0);
     `final_price` = base + tax; create/edit/activate/deactivate; delete allowed
     when unreferenced; audit rows written; STAFF gets 403 on writes.
   - Customer: create requires name + phone + address; phone/email uniqueness
     (409); duplicate-name+phone returns a warning but 201; soft-delete hides from
     default list and `is_active=false` filter shows it; reactivate; address CRUD
     + single-primary invariant; code format `CUST-000001` / `PKG-00001`.
   - Code generator: sequential, zero-padded, prefix from settings.

10. Deliverables check before finishing:
    - `alembic upgrade head` then `alembic downgrade base` succeed on a clean DB;
      re-`upgrade` succeeds.
    - `make check` (ruff + mypy strict over `app`/`scripts` + pytest) is green.
    - New endpoints appear in `/docs`; a manual run creates a package and a
      customer end to end.
    - Update `backend/README.md` (new endpoints) and record open items at the end
      of this file.
    - Commit on a feature branch, open a PR, confirm CI is green.

# Status — Milestone 2 complete (2026-09-10)

Delivered on branch `feat-customers-packages`:

- **Code generator** (`app/services/code_service.py`): per-entity Postgres
  sequence (`customer_code_seq`, `package_code_seq`) + prefix/width from
  `settings` → `CUST-000001` / `PKG-00001`. Sequences bound to metadata for tests
  and created by the migration for real DBs.
- **Packages**: `Package` model + enum `package_status`; migration
  `0002_customers_and_packages`; check constraints for meals (1–500), validity
  (1–730), non-negative prices; `final_price = base + tax` (computed on create
  and every update). Endpoints list/get (STAFF) and create/patch/activate/
  deactivate/delete (ADMIN). `delete` guarded by
  `package_service.is_package_referenced()` — returns `False` now, M3 fills the
  body. Audit: `PACKAGE_CREATED/UPDATED/ACTIVATED/DEACTIVATED/DELETED`.
- **Customers**: `Customer` + `CustomerAddress` models, enum `dietary_pref`;
  `citext` unique email, unique phone (normalised: spaces/dashes/parens
  stripped), soft-delete only (no hard-delete endpoint), separate `allergies`
  field. Endpoints: search (`q`/`phone`/`code`/`is_active`, paginated), create
  (requires ≥ 1 address), detail (with addresses), patch, deactivate/reactivate
  (ADMIN, reason required on deactivate). Duplicate-name → `POSSIBLE_DUPLICATE`
  warning in the `{data, warnings}` envelope, still 201. Audit:
  `CUSTOMER_CREATED/UPDATED/DEACTIVATED/REACTIVATED` +
  `CUSTOMER_ADDRESS_ADDED/UPDATED/REMOVED`.
- **Addresses**: structured fields; exactly one primary per customer (partial
  unique index + two-phase flush so it's never transiently violated); a customer
  always keeps ≥ 1 active address (delete of the last one → 409 `LAST_ADDRESS`);
  removing the primary promotes the next active address.
- `DataWithWarnings[T]` success envelope added to `app/schemas/common.py`.
- `TimestampMixin.updated_at` switched to a Python-side `onupdate` (avoids a
  post-flush refetch / lazy IO under the async engine).
- Tests: `test_packages.py`, `test_customers.py`, `test_code_service.py` —
  **42 pass** total. `conftest` now restarts the code sequences per test
  (sequences are non-transactional).
- `backend/README.md` updated with the endpoint table.

Verified locally: ruff, mypy(strict), `alembic upgrade head` /
`downgrade base` / re-upgrade, 42/42 pytest, and a live run creating a package
(`PKG-00001`, `final_price` 6825.00) and a customer (`CUST-000001`, normalised
phone, duplicate-name warning).

# Open questions / deferred

- **`is_package_referenced()`** is a stub returning `False`. Milestone 3 must
  replace the body with an `EXISTS` against `subscriptions` and add a test that
  a used package cannot be deleted (only deactivated) — BR-6.
- **Phone normalisation** is minimal (strips spaces/dashes/parens/dots; keeps a
  leading `+` and country code). `+919000011111` and `9000011111` are treated as
  different numbers. Revisit if staff routinely enter numbers without the
  country code.
- **Duplicate detection** matches on exact normalised name only
  (case- and whitespace-insensitive). No fuzzy/trigram matching, no
  phone-similarity check. `pg_trgm` is a candidate if false negatives matter.
- **Address `RESTRICT` FK**: `customer_addresses.customer_id` is `ON DELETE
  RESTRICT`, but customers are never hard-deleted, so this only matters if a
  future admin tool bypasses the soft-delete path.
- **`subscriptions` summary on customer detail** (`tech_doc.md` §8) is not in
  `CustomerDetail` yet — added in Milestone 3.
- **CSV import/export** for customers/packages (`tech_doc.md` §9.3, §10.7) is
  Milestone 6, not this phase.
