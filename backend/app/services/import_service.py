"""Stateless CSV customer import — validate, then optionally commit
(tech_doc.md §10.7, Q10.7).

This is deliberately not the two-phase job model in tech_doc.md §10 — one admin
doing occasional imports does not need a job table. See phase_seven.md.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.models.enums import DeliveryFrequency, PackageStatus, TimeSlot
from app.models.package import Package
from app.repositories import customer_repo
from app.schemas.customer import AddressCreate, CustomerCreate
from app.schemas.imports import ImportReport, RowError
from app.schemas.subscription import SubscriptionCreate
from app.services import audit_service, customer_service, subscription_service
from app.services.customer_service import _normalize_phone

REQUIRED_COLUMNS = ("name", "phone", "address_line", "area", "city", "pincode")
_MAX_ERRORS = 200


@dataclass
class _Row:
    number: int
    customer: CustomerCreate | None
    package_code: str | None
    sub_fields: dict[str, object]
    errors: list[RowError] = field(default_factory=list)


def _build_customer(number: int, data: dict[str, str], errors: list[RowError]) -> (
    CustomerCreate | None
):
    try:
        return CustomerCreate(
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            email=data.get("email") or None,
            default_dietary_preference=(data.get("dietary_preference") or None),
            dietary_notes=data.get("dietary_notes") or None,
            allergies=data.get("allergies") or None,
            notes=data.get("notes") or None,
            addresses=[
                AddressCreate(
                    address_line=data.get("address_line", ""),
                    area=data.get("area", ""),
                    city=data.get("city", ""),
                    pincode=data.get("pincode", ""),
                    landmark=data.get("landmark") or None,
                    delivery_notes=data.get("delivery_notes") or None,
                )
            ],
        )
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "row"
            errors.append(RowError(row=number, field=loc, message=err["msg"]))
        return None


def _build_subscription_fields(
    number: int, data: dict[str, str], errors: list[RowError]
) -> dict[str, object]:
    fields: dict[str, object] = {}

    raw_start = data.get("start_date")
    if not raw_start:
        errors.append(
            RowError(row=number, field="start_date", message="required with package_code")
        )
    else:
        try:
            fields["start_date"] = date.fromisoformat(raw_start)
        except ValueError:
            errors.append(RowError(row=number, field="start_date", message="not a date"))

    try:
        fields["delivery_frequency"] = DeliveryFrequency(
            (data.get("delivery_frequency") or "DAILY").upper()
        )
    except ValueError:
        errors.append(
            RowError(row=number, field="delivery_frequency", message="unknown value")
        )

    try:
        fields["delivery_time_slots"] = [TimeSlot((data.get("time_slot") or "MORNING").upper())]
    except ValueError:
        errors.append(RowError(row=number, field="time_slot", message="unknown value"))

    if data.get("delivery_weekdays"):
        try:
            fields["delivery_weekdays"] = [
                int(x) for x in data["delivery_weekdays"].split(",") if x.strip()
            ]
        except ValueError:
            errors.append(
                RowError(row=number, field="delivery_weekdays", message="expected CSV 1-7")
            )
    if data.get("meals_per_delivery"):
        try:
            fields["meals_per_delivery"] = int(data["meals_per_delivery"])
        except ValueError:
            errors.append(
                RowError(row=number, field="meals_per_delivery", message="not an integer")
            )
    return fields


def _parse(text: str) -> tuple[list[_Row], list[RowError]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [RowError(row=0, field="file", message="empty file")]
    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        return [], [
            RowError(row=0, field=c, message="required column missing") for c in missing
        ]

    rows: list[_Row] = []
    seen_phone: dict[str, int] = {}
    seen_email: dict[str, int] = {}

    for number, raw in enumerate(reader, start=2):  # row 1 is the header
        errors: list[RowError] = []
        data = {k: (v or "").strip() for k, v in raw.items() if k}
        customer = _build_customer(number, data, errors)

        if customer is not None:
            phone = _normalize_phone(customer.phone)
            if phone in seen_phone:
                errors.append(
                    RowError(row=number, field="phone",
                             message=f"duplicate of row {seen_phone[phone]}")
                )
            seen_phone.setdefault(phone, number)
            if customer.email:
                key = customer.email.lower()
                if key in seen_email:
                    errors.append(
                        RowError(row=number, field="email",
                                 message=f"duplicate of row {seen_email[key]}")
                    )
                seen_email.setdefault(key, number)

        pkg_code = data.get("package_code") or None
        sub_fields = (
            _build_subscription_fields(number, data, errors) if pkg_code else {}
        )
        rows.append(_Row(number, customer, pkg_code, sub_fields, errors))

    return rows, []


async def _package_by_code(session: AsyncSession, code: str) -> Package | None:
    return (
        await session.execute(select(Package).where(Package.package_code == code))
    ).scalar_one_or_none()


async def _validate_against_db(session: AsyncSession, rows: list[_Row]) -> None:
    for row in rows:
        if row.errors or row.customer is None:
            continue
        if await customer_repo.get_by_phone(
            session, _normalize_phone(row.customer.phone)
        ):
            row.errors.append(
                RowError(row=row.number, field="phone", message="already exists")
            )
        if row.customer.email and await customer_repo.get_by_email(
            session, row.customer.email
        ):
            row.errors.append(
                RowError(row=row.number, field="email", message="already exists")
            )
        if row.package_code:
            pkg = await _package_by_code(session, row.package_code)
            if pkg is None:
                row.errors.append(
                    RowError(row=row.number, field="package_code", message="not found")
                )
            elif pkg.status is not PackageStatus.ACTIVE:
                row.errors.append(
                    RowError(
                        row=row.number, field="package_code", message="package inactive"
                    )
                )


async def import_customers(
    session: AsyncSession, content: bytes, *, commit: bool, actor_id: int | None
) -> ImportReport:
    rows, file_errors = _parse(content.decode("utf-8-sig"))
    if file_errors:
        raise ValidationError(
            "The file is empty or missing required columns",
            code="IMPORT_BAD_FILE",
            details=[e.model_dump() for e in file_errors],
        )

    await _validate_against_db(session, rows)
    all_errors = [e for row in rows for e in row.errors]
    valid = [row for row in rows if not row.errors]

    report = ImportReport(
        total=len(rows),
        valid=len(valid),
        invalid=len(rows) - len(valid),
        committed=False,
        errors=all_errors[:_MAX_ERRORS],
    )
    if not commit:
        return report
    if report.invalid > 0:
        raise ValidationError(
            "The file has row errors — nothing was imported",
            code="IMPORT_HAS_ERRORS",
            details=[e.model_dump() for e in all_errors[:_MAX_ERRORS]],
        )

    created_customers = created_subscriptions = 0
    for row in valid:
        assert row.customer is not None
        customer, _ = await customer_service.create_customer(
            session, row.customer, actor_id=actor_id
        )
        created_customers += 1
        if row.package_code:
            pkg = await _package_by_code(session, row.package_code)
            assert pkg is not None
            payload = SubscriptionCreate(
                customer_id=customer.id,
                package_id=pkg.id,
                delivery_address_id=customer.addresses[0].id,
                **row.sub_fields,
            )
            await subscription_service.create_subscription(
                session, payload, actor_id=actor_id
            )
            created_subscriptions += 1

    await audit_service.record(
        session,
        action="CUSTOMERS_IMPORTED",
        entity_type="customer",
        entity_id=None,
        actor_id=actor_id,
        metadata={
            "customers": created_customers,
            "subscriptions": created_subscriptions,
        },
    )
    report.committed = True
    report.created_customers = created_customers
    report.created_subscriptions = created_subscriptions
    return report
