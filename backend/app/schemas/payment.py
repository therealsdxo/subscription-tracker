"""Payment / refund schemas (tech_doc.md §4.6, §7, §8)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod, PaymentStatus

_Amount = Field(gt=0, max_digits=10, decimal_places=2)


class PaymentCreate(BaseModel):
    amount: Decimal = _Amount
    payment_method: PaymentMethod
    payment_date: date | None = None
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    amount: Decimal
    payment_method: PaymentMethod
    reference_number: str | None
    payment_date: date
    notes: str | None
    recorded_by: int | None
    created_at: datetime


class RefundCreate(BaseModel):
    amount: Decimal = _Amount
    refund_date: date | None = None
    reason: str = Field(min_length=1, max_length=500)
    payment_method: PaymentMethod
    reference_number: str | None = Field(default=None, max_length=100)


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    amount: Decimal
    refund_date: date
    reason: str
    payment_method: PaymentMethod
    reference_number: str | None
    recorded_by: int | None
    created_at: datetime


class PaymentSummary(BaseModel):
    payment_status: PaymentStatus
    total_paid: Decimal
    total_refunded: Decimal
    net_paid: Decimal
    outstanding_amount: Decimal
    suggested_refund: Decimal


class SubscriptionPaymentsView(BaseModel):
    summary: PaymentSummary
    payments: list[PaymentOut]
    refunds: list[RefundOut]
