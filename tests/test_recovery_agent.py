import uuid
import pytest

from app.models import Customer, Payment, PolicyAction, PolicyDecision, Recoverability, FailureCategory
from app.schemas.policy import PolicyEvaluation
from app.schemas.recovery_agent import (
    CustomerContext,
    PaymentContext,
    RecoveryAgentAction,
    RecoveryAgentContext,
    RecoveryChannel,
    RecoveryRecommendation,
)
from app.schemas.risk import RiskAssessment
from app.services.recovery_agent import MockLLMClient, RecoveryAgent


def build_test_context(
    decision: PolicyDecision = PolicyDecision.APPROVED,
    amount_in_paise: int = 199900,
    error_code: str = "NETWORK_ERROR",
    phone: str = "+919876543210",
    attempts: int = 0,
    risk_score: int = 85,
    recoverability: Recoverability = Recoverability.HIGH,
    failure_category: FailureCategory = FailureCategory.RECOVERABLE,
) -> RecoveryAgentContext:
    allowed_action = PolicyAction.PAYMENT_LINK if decision == PolicyDecision.APPROVED else PolicyAction.NONE
    return RecoveryAgentContext(
        payment=PaymentContext(
            id=uuid.uuid4(),
            amount_in_paise=amount_in_paise,
            currency="INR",
            status="FAILED",
            error_code=error_code,
            error_description="Network timeout during transaction",
        ),
        customer=CustomerContext(
            id=uuid.uuid4(),
            name="Priya Sharma",
            email="priya.sharma@example.in",
            phone=phone,
            total_payments=5,
            successful_payments=4,
            has_recent_success_in_30_days=True,
        ),
        risk_assessment=RiskAssessment(
            risk_score=risk_score,
            recoverability=recoverability,
            failure_category=failure_category,
            reason=f"Risk score: {risk_score}/100 ({recoverability.value}).",
        ),
        policy_evaluation=PolicyEvaluation(
            decision=decision,
            reason=f"Policy decision {decision.value} evaluated.",
            allowed_action=allowed_action,
        ),
        previous_attempts_count=attempts,
    )


def test_approved_case_produces_payment_link_and_message():
    """Rule: APPROVED case allows PAYMENT_LINK, selects appropriate channel, and generates customer message."""
    agent = RecoveryAgent(provider="mock")
    context = build_test_context(decision=PolicyDecision.APPROVED, phone="+919876543210")

    recommendation = agent.generate_recommendation(context)

    assert recommendation.recommended_action == RecoveryAgentAction.PAYMENT_LINK
    assert recommendation.recommended_channel == RecoveryChannel.WHATSAPP
    assert recommendation.requires_human_review is False
    assert recommendation.customer_message is not None
    assert "Priya Sharma" in recommendation.customer_message
    assert "1,999.00" in recommendation.customer_message
    assert "{{payment_link}}" in recommendation.customer_message

    # Test Email fallback when phone is not provided
    no_phone_context = build_test_context(decision=PolicyDecision.APPROVED, phone=None)
    rec_email = agent.generate_recommendation(no_phone_context)
    assert rec_email.recommended_channel == RecoveryChannel.EMAIL


def test_human_review_case_prevents_automated_action():
    """Rule: HUMAN_REVIEW case flags requires_human_review=True and prevents automated action."""
    agent = RecoveryAgent(provider="mock")
    context = build_test_context(
        decision=PolicyDecision.HUMAN_REVIEW,
        amount_in_paise=3500000,  # ₹35,000 > ₹25,000 limit
    )

    recommendation = agent.generate_recommendation(context)

    assert recommendation.recommended_action == RecoveryAgentAction.NONE
    assert recommendation.recommended_channel == RecoveryChannel.NONE
    assert recommendation.requires_human_review is True
    assert recommendation.customer_message is None
    assert "human review" in recommendation.explanation.lower()


def test_blocked_case_prevents_action_and_message():
    """Rule: BLOCKED case sets action=NONE and channel=NONE."""
    agent = RecoveryAgent(provider="mock")
    context = build_test_context(
        decision=PolicyDecision.BLOCKED,
        error_code="AUTHENTICATION_FAILED",
        failure_category=FailureCategory.NON_RECOVERABLE,
    )

    recommendation = agent.generate_recommendation(context)

    assert recommendation.recommended_action == RecoveryAgentAction.NONE
    assert recommendation.recommended_channel == RecoveryChannel.NONE
    assert recommendation.customer_message is None
    assert recommendation.requires_human_review is False
    assert "blocked" in recommendation.explanation.lower()


def test_stopped_case_prevents_further_action():
    """Rule: STOPPED case (>= 3 attempts) sets action=NONE and channel=NONE."""
    agent = RecoveryAgent(provider="mock")
    context = build_test_context(
        decision=PolicyDecision.BLOCKED,
        attempts=3,
    )

    recommendation = agent.generate_recommendation(context)

    assert recommendation.recommended_action == RecoveryAgentAction.NONE
    assert recommendation.recommended_channel == RecoveryChannel.NONE
    assert recommendation.customer_message is None
    assert "stopped" in recommendation.explanation.lower() or "limit" in recommendation.explanation.lower()


def test_mock_mode_without_api_key():
    """Verify RecoveryAgent defaults to MockLLMClient and functions deterministically without API keys."""
    agent = RecoveryAgent(provider=None, api_key=None)
    assert isinstance(agent.client, MockLLMClient)

    context = build_test_context(decision=PolicyDecision.APPROVED)
    rec = agent.generate_recommendation(context)
    assert rec.recommended_action == RecoveryAgentAction.PAYMENT_LINK


def test_safety_guardrail_enforcement_overrides_hallucinations():
    """Verify programmatic guardrail overrides any unsafe LLM hallucination."""
    context = build_test_context(decision=PolicyDecision.HUMAN_REVIEW)

    # Simulate an unsafe raw recommendation that mistakenly recommended PAYMENT_LINK
    hallucinated_rec = RecoveryRecommendation(
        recommended_channel=RecoveryChannel.WHATSAPP,
        recommended_action=RecoveryAgentAction.PAYMENT_LINK,  # Dangerous override attempt
        explanation="Attempting automated recovery anyway.",
        customer_message="Your risk_score was 85, please pay now.",
        requires_human_review=False,
    )

    safe_rec = RecoveryAgent.enforce_safety_guardrails(context, hallucinated_rec)

    # Safety guardrail must have forcefully overridden it
    assert safe_rec.recommended_action == RecoveryAgentAction.NONE
    assert safe_rec.requires_human_review is True
    assert safe_rec.customer_message is None


def test_generate_from_orm_models():
    """Verify RecoveryAgent works seamlessly with ORM model instances."""
    agent = RecoveryAgent(provider="mock")

    customer = Customer(
        id=uuid.uuid4(),
        name="Vikram Rao",
        email="vikram.rao@example.in",
        phone="+919811223344",
    )
    payment = Payment(
        id=uuid.uuid4(),
        customer_id=customer.id,
        amount_in_paise=249900,
        currency="INR",
        status="FAILED",
        error_code="BANK_ERROR",
    )
    risk_assessment = RiskAssessment(
        risk_score=85,
        recoverability=Recoverability.HIGH,
        failure_category=FailureCategory.RECOVERABLE,
        reason="High recoverability score.",
    )
    policy_evaluation = PolicyEvaluation(
        decision=PolicyDecision.APPROVED,
        reason="Recovery approved.",
        allowed_action=PolicyAction.PAYMENT_LINK,
    )

    rec = agent.generate_from_models(
        payment=payment,
        customer=customer,
        risk_assessment=risk_assessment,
        policy_evaluation=policy_evaluation,
        previous_attempts=0,
    )

    assert rec.recommended_action == RecoveryAgentAction.PAYMENT_LINK
    assert rec.recommended_channel == RecoveryChannel.WHATSAPP
    assert "Vikram Rao" in rec.customer_message
