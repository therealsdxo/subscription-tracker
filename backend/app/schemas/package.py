"""Package request/response schemas (tech_doc.md §4.2, §8)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PackageStatus
from app.models.package import MEALS_MAX, MEALS_MIN, VALIDITY_MAX, VALIDITY_MIN

_Price = Field(ge=0, max_digits=10, decimal_places=2)


class PackageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    number_of_meals: int = Field(ge=MEALS_MIN, le=MEALS_MAX)
    validity_days: int = Field(ge=VALIDITY_MIN, le=VALIDITY_MAX)
    base_price: Decimal = _Price
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class PackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    number_of_meals: int | None = Field(default=None, ge=MEALS_MIN, le=MEALS_MAX)
    validity_days: int | None = Field(default=None, ge=VALIDITY_MIN, le=VALIDITY_MAX)
    base_price: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    tax_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )

    @model_validator(mode="after")
    def _at_least_one_field(self) -> PackageUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("no fields to update")
        return self


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_code: str
    name: str
    description: str | None
    number_of_meals: int
    validity_days: int
    base_price: Decimal
    tax_amount: Decimal
    final_price: Decimal
    status: PackageStatus
    created_at: datetime
    updated_at: datetime
