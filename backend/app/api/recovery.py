import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import (
    AuditEvent,
    Customer,
    Payment,
    PolicyAction,
    PolicyDecision,
    RecoveryAttempt,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.recovery import (
    AuditEventDetail,
    CandidateItemResponse,
    CustomerDetail,
    PaymentDetail,
    RecoveryAttemptDetail,
    RecoveryCaseDetailResponse,
    RecoveryOverviewResponse,
)

logger = logging.getLogger("recoverai.api.recovery")

router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.get("/overview", response_model=RecoveryOverviewResponse)
def get_recovery_overview(db: Session = Depends(get_db)):
    """Get calculated aggregate metrics directly from PostgreSQL."""
    total_failed = (
        db.query(func.count(Payment.id))
        .filter(Payment.status == "FAILED")
        .scalar()
        or 0
    )

    revenue_at_risk = (
        db.query(func.coalesce(func.sum(Payment.amount_in_paise), 0))
        .filter(Payment.status == "FAILED")
        .scalar()
        or 0
    )

    approved_count = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.policy_decision == PolicyDecision.APPROVED)
        .scalar()
        or 0
    )

    human_review_count = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.policy_decision == PolicyDecision.HUMAN_REVIEW)
        .scalar()
        or 0
    )

    blocked_count = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.policy_decision == PolicyDecision.BLOCKED)
        .scalar()
        or 0
    )

    stopped_count = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.status == RecoveryCaseStatus.STOPPED)
        .scalar()
        or 0
    )

    total_attempts = db.query(func.count(RecoveryAttempt.id)).scalar() or 0

    return RecoveryOverviewResponse(
        total_failed_payments=total_failed,
        total_revenue_at_risk_in_paise=revenue_at_risk,
        approved_cases=approved_count,
        human_review_cases=human_review_count,
        blocked_cases=blocked_count,
        stopped_cases=stopped_count,
        total_recovery_attempts=total_attempts,
    )


@router.get("/candidates", response_model=List[CandidateItemResponse])
def get_recovery_candidates(db: Session = Depends(get_db)):
    """Return recovery cases that are currently APPROVED and eligible for automated recovery action."""
    cases = (
        db.query(RecoveryCase)
        .options(
            joinedload(RecoveryCase.payment).joinedload(Payment.customer),
            joinedload(RecoveryCase.audit_events),
        )
        .filter(RecoveryCase.policy_decision == PolicyDecision.APPROVED)
        .order_by(RecoveryCase.created_at.desc())
        .all()
    )

    candidates: List[CandidateItemResponse] = []
    for case in cases:
        pmt = case.payment
        cust = pmt.customer if pmt else None

        # Retrieve risk information from stored audit events payload if available
        risk_score = None
        recoverability = None
        for event in case.audit_events:
            if event.event_type == "POLICY_EVALUATED" and event.payload:
                risk_score = event.payload.get("risk_score")
                recoverability = event.payload.get("recoverability")
                break

        candidates.append(
            CandidateItemResponse(
                recovery_case_id=case.id,
                payment_id=pmt.id if pmt else uuid.UUID(int=0),
                customer_name=cust.name if cust else "Unknown Customer",
                amount_in_paise=pmt.amount_in_paise if pmt else 0,
                currency=pmt.currency if pmt else "INR",
                error_code=pmt.error_code if pmt else None,
                risk_score=risk_score,
                recoverability=recoverability,
                policy_decision=case.policy_decision or PolicyDecision.APPROVED,
                policy_reason=case.policy_reason,
                allowed_action=PolicyAction.PAYMENT_LINK,
            )
        )

    return candidates


@router.get("/cases/{case_id}", response_model=RecoveryCaseDetailResponse)
def get_recovery_case_detail(case_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return detailed information for one recovery case including payment, customer, attempts, and audit trail."""
    case = (
        db.query(RecoveryCase)
        .options(
            joinedload(RecoveryCase.payment).joinedload(Payment.customer),
            joinedload(RecoveryCase.recovery_attempts),
            joinedload(RecoveryCase.audit_events),
        )
        .filter(RecoveryCase.id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case with ID '{case_id}' was not found.",
        )

    pmt = case.payment
    if not pmt or not pmt.customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated payment or customer for recovery case '{case_id}' is missing.",
        )

    # Sort attempts by attempt_number and audit events by created_at
    attempts = sorted(case.recovery_attempts, key=lambda a: a.attempt_number)
    events = sorted(case.audit_events, key=lambda e: e.created_at)

    return RecoveryCaseDetailResponse(
        id=case.id,
        status=case.status,
        policy_decision=case.policy_decision,
        policy_reason=case.policy_reason,
        created_at=case.created_at,
        updated_at=case.updated_at,
        payment=PaymentDetail.model_validate(pmt),
        customer=CustomerDetail.model_validate(pmt.customer),
        recovery_attempts=[RecoveryAttemptDetail.model_validate(a) for a in attempts],
        audit_events=[AuditEventDetail.model_validate(e) for e in events],
    )
