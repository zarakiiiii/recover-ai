from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PolicyDecision, RecoveryCaseStatus

if TYPE_CHECKING:
    from app.models.audit_event import AuditEvent
    from app.models.payment import Payment
    from app.models.recovery_attempt import RecoveryAttempt


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[RecoveryCaseStatus] = mapped_column(
        SQLEnum(RecoveryCaseStatus, name="recovery_case_status"),
        default=RecoveryCaseStatus.PAYMENT_FAILED,
        nullable=False,
        index=True,
    )
    policy_decision: Mapped[Optional[PolicyDecision]] = mapped_column(
        SQLEnum(PolicyDecision, name="policy_decision"),
        nullable=True,
    )
    policy_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="recovery_case",
    )
    recovery_attempts: Mapped[List["RecoveryAttempt"]] = relationship(
        "RecoveryAttempt",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
