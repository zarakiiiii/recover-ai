import uuid
import pytest

from app.models.enums import FailureCategory, PolicyAction, PolicyDecision, Recoverability
from app.models.payment import Payment
from app.schemas.policy import PolicyEvaluation
from app.schemas.risk import RiskAssessment
from app.services.policy_engine import PolicyEngine


def make_assessment(
    risk_score: int = 85,
    recoverability: Recoverability = Recoverability.HIGH,
    failure_category: FailureCategory = FailureCategory.RECOVERABLE,
    reason: str = "Test reason",
) -> RiskAssessment:
    return RiskAssessment(
        risk_score=risk_score,
        recoverability=recoverability,
        failure_category=failure_category,
        reason=reason,
    )


def test_rule_1_max_recovery_attempts_stops_recovery():
    """Rule 1: If previous recovery attempts >= 3 -> STOP (BLOCKED, allowed_action: NONE)."""
    # Even if recoverability is HIGH and amount is low
    assessment = make_assessment(recoverability=Recoverability.HIGH)
    result = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=100_000,  # ₹1,000
        previous_attempts=3,
    )

    assert result.decision == PolicyDecision.BLOCKED
    assert result.allowed_action == PolicyAction.NONE
    assert "STOP" in result.reason
    assert "3" in result.reason

    # Attempts > 3
    result_4 = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=100_000,
        previous_attempts=4,
    )
    assert result_4.decision == PolicyDecision.BLOCKED
    assert result_4.allowed_action == PolicyAction.NONE


def test_rule_2_high_value_transaction_requires_human_review():
    """Rule 2: Else if payment amount > 25,000 INR (2,500,000 paise) -> HUMAN_REVIEW."""
    assessment = make_assessment(recoverability=Recoverability.HIGH)

    # ₹25,001 (2,500,100 paise) -> Trigger Rule 2
    result = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=2_500_100,
        previous_attempts=0,
    )
    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert result.allowed_action == PolicyAction.NONE
    assert "exceeds" in result.reason

    # ₹25,000 exact (2,500,000 paise) -> Should NOT trigger Rule 2, should proceed to Rule 4 (APPROVED)
    result_exact = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=2_500_000,
        previous_attempts=0,
    )
    assert result_exact.decision == PolicyDecision.APPROVED
    assert result_exact.allowed_action == PolicyAction.PAYMENT_LINK


def test_rule_3_non_recoverable_failure_blocks_recovery():
    """Rule 3: Else if failure category is NON_RECOVERABLE -> BLOCKED."""
    # Even if recoverability score was medium/high
    assessment = make_assessment(
        risk_score=60,
        recoverability=Recoverability.MEDIUM,
        failure_category=FailureCategory.NON_RECOVERABLE,
    )

    result = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=500_000,  # ₹5,000
        previous_attempts=0,
    )
    assert result.decision == PolicyDecision.BLOCKED
    assert result.allowed_action == PolicyAction.NONE
    assert "NON_RECOVERABLE" in result.reason


def test_rule_4_high_recoverability_approves_payment_link():
    """Rule 4: Else if recoverability is HIGH -> APPROVED (allowed_action: PAYMENT_LINK)."""
    assessment = make_assessment(
        risk_score=85,
        recoverability=Recoverability.HIGH,
        failure_category=FailureCategory.RECOVERABLE,
    )

    result = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        amount_in_paise=1_000_000,  # ₹10,000
        previous_attempts=1,
    )
    assert result.decision == PolicyDecision.APPROVED
    assert result.allowed_action == PolicyAction.PAYMENT_LINK
    assert "approved" in result.reason.lower()


def test_rule_5_moderate_or_low_recoverability_fallback_to_human_review():
    """Rule 5: Else -> HUMAN_REVIEW."""
    # Medium recoverability with recoverable category
    med_assessment = make_assessment(
        risk_score=60,
        recoverability=Recoverability.MEDIUM,
        failure_category=FailureCategory.RECOVERABLE,
    )
    res_med = PolicyEngine.evaluate_policy(
        risk_assessment=med_assessment,
        amount_in_paise=500_000,
        previous_attempts=0,
    )
    assert res_med.decision == PolicyDecision.HUMAN_REVIEW
    assert res_med.allowed_action == PolicyAction.NONE

    # Low recoverability with uncertain category
    low_assessment = make_assessment(
        risk_score=20,
        recoverability=Recoverability.LOW,
        failure_category=FailureCategory.UNCERTAIN,
    )
    res_low = PolicyEngine.evaluate_policy(
        risk_assessment=low_assessment,
        amount_in_paise=500_000,
        previous_attempts=0,
    )
    assert res_low.decision == PolicyDecision.HUMAN_REVIEW
    assert res_low.allowed_action == PolicyAction.NONE


def test_policy_evaluation_with_payment_orm():
    """Verify policy evaluation with a Payment ORM model."""
    payment = Payment(
        id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        amount_in_paise=150_000,  # ₹1,500
        currency="INR",
        status="FAILED",
        error_code="NETWORK_ERROR",
    )
    assessment = make_assessment(recoverability=Recoverability.HIGH)

    result = PolicyEngine.evaluate_policy(
        risk_assessment=assessment,
        payment=payment,
        previous_attempts=0,
    )
    assert result.decision == PolicyDecision.APPROVED
    assert result.allowed_action == PolicyAction.PAYMENT_LINK
