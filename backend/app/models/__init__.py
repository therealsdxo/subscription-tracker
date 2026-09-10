"""SQLAlchemy models. Import all here so Alembic autogenerate sees them."""

from app.models import sequences as sequences  # noqa: F401 - registers sequences
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.customer import Customer, CustomerAddress
from app.models.package import Package
from app.models.setting import Setting
from app.models.subscription import MealAdjustment, Subscription, SubscriptionEvent
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Customer",
    "CustomerAddress",
    "MealAdjustment",
    "Package",
    "Setting",
    "Subscription",
    "SubscriptionEvent",
    "User",
]
