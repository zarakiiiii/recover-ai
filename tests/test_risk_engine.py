from datetime import datetime, timedelta, timezone
import uuid
import pytest

from app.models.enums import FailureCategory, Recoverability
from app.models.payment import Payment
from app.schemas.risk import CustomerPaymentHistory, RiskAssessment
from app.services.risk_engine import RiskEngine


def test_customer_history_scoring_brackets():
    """Verify customer history score brackets: >=80% -> +30, 50-79% -> +15, <50% -> +0."""
    assert RiskEngine.calculate_history_score(100.0) == 30
    assert RiskEngine.calculate_history_score(85.0) == 30
    assert RiskEngine.calculate_history_score(80.0) == 30

    assert RiskEngine.calculate_history_score(79.9) == 15
    assert RiskEngine.calculate_history_score(60.0) == 15
    assert RiskEngine.calculate_history_score(50.0) == 15

    assert RiskEngine.calculate_history_score(49.9) == 0
    assert RiskEngine.calculate_history_score(20.0) == 0
    assert RiskEngine.calculate_history_score(0.0) == 0


def test_failure_type_scoring_and_categories():
    """Verify failure type scoring (+25, +15, +0) and categorization."""
    # Network / Bank Error -> +25, RECOVERABLE
    assert RiskEngine.calculate_failure_type_score("NETWORK_ERROR") == 25
    assert RiskEngine.calculate_failure_type_score("BANK_ERROR") == 25
    assert RiskEngine.classify_failure_category("NETWORK_ERROR") == FailureCategory.RECOVERABLE
    assert RiskEngine.classify_failure_category("bank_error") == FailureCategory.RECOVERABLE

    # Card / Funds Error -> +15, RECOVERABLE
    assert RiskEngine.calculate_failure_type_score("CARD_DECLINED") == 15
    assert RiskEngine.calculate_failure_type_score("EXPIRED_CARD") == 15
    assert RiskEngine.calculate_failure_type_score("INSUFFICIENT_FUNDS") == 15
    assert RiskEngine.classify_failure_category("CARD_DECLINED") == FailureCategory.RECOVERABLE
    assert RiskEngine.classify_failure_category("insufficient_funds") == FailureCategory.RECOVERABLE

    # Auth Failed -> +0, NON_RECOVERABLE
    assert RiskEngine.calculate_failure_type_score("AUTHENTICATION_FAILED") == 0
    assert RiskEngine.classify_failure_category("AUTHENTICATION_FAILED") == FailureCategory.NON_RECOVERABLE

    # Unknown / None -> +0, UNCERTAIN
    assert RiskEngine.calculate_failure_type_score("UNKNOWN_CUSTOM_ERROR") == 0
    assert RiskEngine.calculate_failure_type_score(None) == 0
    assert RiskEngine.classify_failure_category("UNKNOWN_CUSTOM_ERROR") == FailureCategory.UNCERTAIN
    assert RiskEngine.classify_failure_category(None) == FailureCategory.UNCERTAIN


def test_recovery_attempts_scoring():
    """Verify recovery attempts scoring: 0 -> +10, 1 -> +5, >=2 -> +0."""
    assert RiskEngine.calculate_attempts_score(0) == 10
    assert RiskEngine.calculate_attempts_score(1) == 5
    assert RiskEngine.calculate_attempts_score(2) == 0
    assert RiskEngine.calculate_attempts_score(5) == 0


def test_recoverability_mapping():
    """Verify recoverability ratings: 80-100 HIGH, 50-79 MEDIUM, 0-49 LOW."""
    assert RiskEngine.calculate_recoverability(100) == Recoverability.HIGH
    assert RiskEngine.calculate_recoverability(85) == Recoverability.HIGH
    assert RiskEngine.calculate_recoverability(80) == Recoverability.HIGH

    assert RiskEngine.calculate_recoverability(79) == Recoverability.MEDIUM
    assert RiskEngine.calculate_recoverability(60) == Recoverability.MEDIUM
    assert RiskEngine.calculate_recoverability(50) == Recoverability.MEDIUM

    assert RiskEngine.calculate_recoverability(49) == Recoverability.LOW
    assert RiskEngine.calculate_recoverability(20) == Recoverability.LOW
    assert RiskEngine.calculate_recoverability(0) == Recoverability.LOW


def test_high_recoverability_scenario():
    """Customer with 90% success rate, recent payment in 10 days, network error, 0 attempts -> 30+20+25+10 = 85 -> HIGH."""
    history = CustomerPaymentHistory(
        total_payments=10,
        successful_payments=9,
        has_recent_success_in_30_days=True,
    )
    assessment: RiskAssessment = RiskEngine.assess_risk(
        error_code="NETWORK_ERROR",
        customer_history=history,
        previous_attempts=0,
    )

    assert assessment.risk_score == 85
    assert assessment.recoverability == Recoverability.HIGH
    assert assessment.failure_category == FailureCategory.RECOVERABLE
    assert assessment.breakdown["history_score"] == 30
    assert assessment.breakdown["recent_success_score"] == 20
    assert assessment.breakdown["failure_type_score"] == 25
    assert assessment.breakdown["attempts_score"] == 10
    assert "85/100 (HIGH)" in assessment.reason


def test_medium_recoverability_scenario():
    """Customer with 60% success rate (+15), no recent success (+0), card declined (+15), 1 attempt (+5) -> 35 -> LOW, but with recent success (+20) -> 55 -> MEDIUM."""
    history = CustomerPaymentHistory(
        total_payments=5,
        successful_payments=3,
        has_recent_success_in_30_days=True,
    )
    assessment = RiskEngine.assess_risk(
        error_code="CARD_DECLINED",
        customer_history=history,
        previous_attempts=1,
    )

    # 15 (history) + 20 (recent) + 15 (card declined) + 5 (1 attempt) = 55
    assert assessment.risk_score == 55
    assert assessment.recoverability == Recoverability.MEDIUM
    assert assessment.failure_category == FailureCategory.RECOVERABLE


def test_non_recoverable_auth_failed_scenario():
    """Authentication failed error produces NON_RECOVERABLE category."""
    history = CustomerPaymentHistory(
        total_payments=2,
        successful_payments=2,
        has_recent_success_in_30_days=True,
    )
    assessment = RiskEngine.assess_risk(
        error_code="AUTHENTICATION_FAILED",
        customer_history=history,
        previous_attempts=0,
    )

    # 30 + 20 + 0 + 10 = 60 (MEDIUM score, but NON_RECOVERABLE category)
    assert assessment.risk_score == 60
    assert assessment.failure_category == FailureCategory.NON_RECOVERABLE


def test_assess_risk_with_payment_orm_model():
    """Test assess_risk using Payment SQLAlchemy ORM objects and payment history."""
    ref_time = datetime.now(timezone.utc)
    cust_id = uuid.uuid4()

    current_payment = Payment(
        id=uuid.uuid4(),
        customer_id=cust_id,
        amount_in_paise=500_000,
        currency="INR",
        status="FAILED",
        error_code="BANK_ERROR",
        created_at=ref_time,
    )

    past_payment_1 = Payment(
        id=uuid.uuid4(),
        customer_id=cust_id,
        amount_in_paise=500_000,
        currency="INR",
        status="SUCCESS",
        created_at=ref_time - timedelta(days=5),
    )
    past_payment_2 = Payment(
        id=uuid.uuid4(),
        customer_id=cust_id,
        amount_in_paise=500_000,
        currency="INR",
        status="SUCCESS",
        created_at=ref_time - timedelta(days=40),
    )

    assessment = RiskEngine.assess_risk(
        payment=current_payment,
        customer_history=[past_payment_1, past_payment_2],
        previous_attempts=0,
        reference_time=ref_time,
    )

    # 2 past payments, 2 successful -> 100% success rate (+30)
    # past_payment_1 is within 5 days -> (+20)
    # BANK_ERROR -> (+25)
    # 0 previous attempts -> (+10)
    # Total = 85 -> HIGH
    assert assessment.risk_score == 85
    assert assessment.recoverability == Recoverability.HIGH
    assert assessment.failure_category == FailureCategory.RECOVERABLE
