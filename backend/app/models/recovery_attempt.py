from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecoveryAction, RecoveryAttemptStatus

if TYPE_CHECKING:
    from app.models.recovery_case import RecoveryCase


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recovery_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    action: Mapped[RecoveryAction] = mapped_column(
        SQLEnum(RecoveryAction, name="recovery_action"),
        default=RecoveryAction.PAYMENT_LINK,
        nullable=False,
    )
    status: Mapped[RecoveryAttemptStatus] = mapped_column(
        SQLEnum(RecoveryAttemptStatus, name="recovery_attempt_status"),
        default=RecoveryAttemptStatus.PENDING,
        nullable=False,
        index=True,
    )
    channel: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
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
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase",
        back_populates="recovery_attempts",
    )
