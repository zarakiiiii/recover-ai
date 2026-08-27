from datetime import datetime, timezone
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
    RecoveryAction,
    RecoveryAttempt,
    RecoveryAttemptStatus,
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
    RecoveryExecutionResponse,
    RecoveryOverviewResponse,
)
from app.schemas.recovery_agent import RecoveryChannel
from app.services.policy_engine import PolicyEngine
from app.services.recovery_agent import RecoveryAgent
from app.services.risk_engine import RiskEngine

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


@router.post("/cases/{case_id}/execute", response_model=RecoveryExecutionResponse)
def execute_recovery_case(case_id: uuid.UUID, db: Session = Depends(get_db)):
    """Execute automated recovery for an APPROVED case, generating a mock payment link, persisting attempt, and updating audit trail."""
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Associated payment or customer data for case '{case_id}' is missing.",
        )

    # Safety checks: never execute non-eligible cases
    if case.status == RecoveryCaseStatus.STOPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery case is STOPPED. Automated recovery is not permitted.",
        )

    attempts_count = len(case.recovery_attempts)
    if attempts_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum recovery attempts ({attempts_count}) reached. Recovery execution is stopped.",
        )

    if case.policy_decision != PolicyDecision.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Case '{case_id}' is not authorized for automated recovery "
                f"(Policy Decision: {case.policy_decision.value}). Reason: {case.policy_reason}"
            ),
        )

    # Re-evaluate risk and policy dynamically to verify eligibility
    risk_assessment = RiskEngine.assess_risk(
        payment=pmt,
        previous_attempts=attempts_count,
    )
    policy_eval = PolicyEngine.evaluate_policy(
        risk_assessment=risk_assessment,
        payment=pmt,
        previous_attempts=attempts_count,
    )

    if policy_eval.decision != PolicyDecision.APPROVED or policy_eval.allowed_action != PolicyAction.PAYMENT_LINK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Re-evaluation failed policy approval: {policy_eval.reason}",
        )

    # Generate recommendation using AI Recovery Agent
    agent = RecoveryAgent()
    rec = agent.generate_from_models(
        payment=pmt,
        customer=pmt.customer,
        risk_assessment=risk_assessment,
        policy_evaluation=policy_eval,
        previous_attempts=attempts_count,
    )

    # Prepare attempt parameters
    attempt_number = attempts_count + 1
    channel = rec.recommended_channel.value if rec.recommended_channel != RecoveryChannel.NONE else "WHATSAPP"

    # Deterministic mock payment link generation
    payment_link_id = f"plink_mock_{uuid.uuid4().hex[:10]}"
    payment_link_url = f"https://pay.recoverai.internal/mock/{payment_link_id}"

    # Build customer-facing message with payment link
    raw_message = rec.customer_message or (
        f"Hi {pmt.customer.name}, your payment of INR {pmt.amount_in_paise / 100:,.2f} could not be completed. "
        f"Please complete your payment securely here: {{{{payment_link}}}}."
    )
    final_message = raw_message.replace("{{payment_link}}", payment_link_url)

    now = datetime.now(timezone.utc)

    # 1. Record AuditEvent: RECOVERY_EXECUTION_STARTED
    audit_start = AuditEvent(
        id=uuid.uuid4(),
        recovery_case_id=case.id,
        event_type="RECOVERY_EXECUTION_STARTED",
        from_state=case.status.value,
        to_state="EXECUTING",
        actor="RECOVERY_AGENT",
        payload={
            "attempt_number": attempt_number,
            "channel": channel,
            "action": RecoveryAction.PAYMENT_LINK.value,
            "payment_link_id": payment_link_id,
        },
        created_at=now,
    )
    db.add(audit_start)

    # 2. Create RecoveryAttempt record
    attempt = RecoveryAttempt(
        id=uuid.uuid4(),
        recovery_case_id=case.id,
        attempt_number=attempt_number,
        action=RecoveryAction.PAYMENT_LINK,
        status=RecoveryAttemptStatus.SUCCESS,  # In mock execution, marked SUCCESS
        channel=channel,
        details={
            "mock_execution": True,
            "gateway": "mock_razorpay",
            "payment_link_id": payment_link_id,
            "payment_link_url": payment_link_url,
            "message_sent": final_message,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(attempt)

    # 3. Update RecoveryCase status
    case.status = RecoveryCaseStatus.RECOVERED
    case.updated_at = now

    # 4. Record AuditEvent: RECOVERY_EXECUTION_COMPLETED
    audit_complete = AuditEvent(
        id=uuid.uuid4(),
        recovery_case_id=case.id,
        event_type="RECOVERY_EXECUTION_COMPLETED",
        from_state="EXECUTING",
        to_state="RECOVERED",
        actor="RECOVERY_AGENT",
        payload={
            "attempt_id": str(attempt.id),
            "attempt_number": attempt_number,
            "status": RecoveryAttemptStatus.SUCCESS.value,
            "payment_link_url": payment_link_url,
        },
        created_at=now,
    )
    db.add(audit_complete)

    db.commit()
    db.refresh(attempt)
    db.refresh(case)

    logger.info(
        f"Successfully executed recovery for case '{case.id}'. Attempt #{attempt_number} created (ID: {attempt.id})."
    )

    return RecoveryExecutionResponse(
        recovery_case_id=case.id,
        attempt_id=attempt.id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        action=attempt.action,
        channel=attempt.channel,
        payment_link=payment_link_url,
        message=final_message,
    )
