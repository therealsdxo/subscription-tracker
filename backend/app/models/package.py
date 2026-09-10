"""``packages`` — meal subscription packages (tech_doc.md §3.3, §4.2)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PackageStatus

MEALS_MIN, MEALS_MAX = 1, 500
VALIDITY_MIN, VALIDITY_MAX = 1, 730


class Package(TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint(
            f"number_of_meals BETWEEN {MEALS_MIN} AND {MEALS_MAX}",
            name="meals_in_range",
        ),
        CheckConstraint(
            f"validity_days BETWEEN {VALIDITY_MIN} AND {VALIDITY_MAX}",
            name="validity_in_range",
        ),
        CheckConstraint("base_price >= 0", name="base_price_non_negative"),
        CheckConstraint("tax_amount >= 0", name="tax_amount_non_negative"),
        CheckConstraint("final_price >= 0", name="final_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    package_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    number_of_meals: Mapped[int] = mapped_column(nullable=False)
    validity_days: Mapped[int] = mapped_column(nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    final_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PackageStatus] = mapped_column(
        SAEnum(PackageStatus, name="package_status", native_enum=True),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Package {self.package_code} {self.name!r} {self.status.value}>"
