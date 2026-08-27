from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    PolicyAction,
    PolicyDecision,
    RecoveryAction,
    RecoveryAttemptStatus,
    RecoveryCaseStatus,
)


class RecoveryOverviewResponse(BaseModel):
    """Aggregate recovery metrics calculated from PostgreSQL."""
    total_failed_payments: int = Field(..., description="Total count of failed payments")
    total_revenue_at_risk_in_paise: int = Field(..., description="Total amount in paise at risk from failed payments")
    approved_cases: int = Field(..., description="Count of recovery cases with APPROVED policy decision")
    human_review_cases: int = Field(..., description="Count of recovery cases requiring HUMAN_REVIEW")
    blocked_cases: int = Field(..., description="Count of recovery cases BLOCKED by policy")
    stopped_cases: int = Field(..., description="Count of recovery cases in STOPPED status")
    total_recovery_attempts: int = Field(..., description="Total recovery attempts recorded")


class CandidateItemResponse(BaseModel):
    """Candidate recovery case item eligible for automated recovery."""
    recovery_case_id: uuid.UUID
    payment_id: uuid.UUID
    customer_name: str
    amount_in_paise: int
    currency: str = "INR"
    error_code: Optional[str] = None
    risk_score: Optional[int] = None
    recoverability: Optional[str] = None
    policy_decision: PolicyDecision
    policy_reason: Optional[str] = None
    allowed_action: PolicyAction = PolicyAction.PAYMENT_LINK


class CustomerDetail(BaseModel):
    """Customer summary detail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime


class PaymentDetail(BaseModel):
    """Payment summary detail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount_in_paise: int
    currency: str
    status: str
    gateway: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    created_at: datetime


class RecoveryAttemptDetail(BaseModel):
    """Recovery attempt detail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_number: int
    action: RecoveryAction
    status: RecoveryAttemptStatus
    channel: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditEventDetail(BaseModel):
    """Audit event detail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    actor: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class RecoveryCaseDetailResponse(BaseModel):
    """Complete detail of a single recovery case including customer, payment, attempts, and audit trail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: RecoveryCaseStatus
    policy_decision: Optional[PolicyDecision] = None
    policy_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    payment: PaymentDetail
    customer: CustomerDetail
    recovery_attempts: List[RecoveryAttemptDetail] = []
    audit_events: List[AuditEventDetail] = []


class RecoveryExecutionResponse(BaseModel):
    """Structured response returned upon executing an approved recovery case."""
    recovery_case_id: uuid.UUID
    attempt_id: uuid.UUID
    attempt_number: int
    status: RecoveryAttemptStatus
    action: RecoveryAction
    channel: str
    payment_link: str
    message: str
