"""Customer + address request/response schemas (tech_doc.md §3.3, §8)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import DietaryPreference
from app.schemas.subscription import CustomerSubscriptionSummary


class AddressBase(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    address_line: str = Field(min_length=1, max_length=500)
    area: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=120)
    pincode: str = Field(min_length=3, max_length=16)
    landmark: str | None = Field(default=None, max_length=200)
    delivery_notes: str | None = Field(default=None, max_length=1000)


class AddressCreate(AddressBase):
    is_primary: bool = False


class AddressUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    address_line: str | None = Field(default=None, min_length=1, max_length=500)
    area: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    pincode: str | None = Field(default=None, min_length=3, max_length=16)
    landmark: str | None = Field(default=None, max_length=200)
    delivery_notes: str | None = Field(default=None, max_length=1000)
    is_primary: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> AddressUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("no fields to update")
        return self


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str | None
    address_line: str
    area: str
    city: str
    pincode: str
    landmark: str | None
    delivery_notes: str | None
    is_primary: bool
    is_active: bool


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=4, max_length=32)
    email: EmailStr | None = None
    default_dietary_preference: DietaryPreference | None = None
    dietary_notes: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    addresses: list[AddressCreate] = Field(min_length=1)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=4, max_length=32)
    email: EmailStr | None = None
    default_dietary_preference: DietaryPreference | None = None
    dietary_notes: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> CustomerUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("no fields to update")
        return self


class CustomerDeactivate(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_code: str
    name: str
    phone: str
    email: EmailStr | None
    default_dietary_preference: DietaryPreference | None
    dietary_notes: str | None
    allergies: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerDetail(CustomerOut):
    addresses: list[AddressOut] = Field(default_factory=list)
    subscriptions: CustomerSubscriptionSummary = Field(
        default_factory=CustomerSubscriptionSummary
    )
