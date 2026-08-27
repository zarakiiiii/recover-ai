from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Union

from app.models.enums import FailureCategory, Recoverability
from app.models.payment import Payment
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.risk import CustomerPaymentHistory, RiskAssessment

# Error code classification
RECOVERABLE_HIGH_SCORE_TYPES = {"NETWORK_ERROR", "BANK_ERROR"}
RECOVERABLE_MED_SCORE_TYPES = {"CARD_DECLINED", "EXPIRED_CARD", "INSUFFICIENT_FUNDS"}
NON_RECOVERABLE_TYPES = {"AUTHENTICATION_FAILED"}


class RiskEngine:
    """Deterministic Revenue Risk Engine for analyzing failed payments."""

    @staticmethod
    def classify_failure_category(error_code: Optional[str]) -> FailureCategory:
        """Classify failure type into RECOVERABLE, NON_RECOVERABLE, or UNCERTAIN."""
        if not error_code:
            return FailureCategory.UNCERTAIN

        normalized = error_code.strip().upper()
        if normalized in RECOVERABLE_HIGH_SCORE_TYPES or normalized in RECOVERABLE_MED_SCORE_TYPES:
            return FailureCategory.RECOVERABLE
        if normalized in NON_RECOVERABLE_TYPES:
            return FailureCategory.NON_RECOVERABLE
        return FailureCategory.UNCERTAIN

    @staticmethod
    def calculate_failure_type_score(error_code: Optional[str]) -> int:
        """Calculate points based on failure error code."""
        if not error_code:
            return 0

        normalized = error_code.strip().upper()
        if normalized in RECOVERABLE_HIGH_SCORE_TYPES:
            return 25
        if normalized in RECOVERABLE_MED_SCORE_TYPES:
            return 15
        if normalized in NON_RECOVERABLE_TYPES:
            return 0
        return 0

    @staticmethod
    def calculate_history_score(success_rate: float) -> int:
        """Calculate points based on customer's historical payment success rate."""
        if success_rate >= 80.0:
            return 30
        if success_rate >= 50.0:
            return 15
        return 0

    @staticmethod
    def calculate_attempts_score(previous_attempts: int) -> int:
        """Calculate points based on previous recovery attempts."""
        if previous_attempts == 0:
            return 10
        if previous_attempts == 1:
            return 5
        return 0

    @staticmethod
    def calculate_recoverability(score: int) -> Recoverability:
        """Map score (0-100) to Recoverability rating."""
        if score >= 80:
            return Recoverability.HIGH
        if score >= 50:
            return Recoverability.MEDIUM
        return Recoverability.LOW

    @classmethod
    def assess_risk(
        cls,
        payment: Optional[Payment] = None,
        *,
        error_code: Optional[str] = None,
        customer_history: Optional[Union[CustomerPaymentHistory, Sequence[Payment]]] = None,
        previous_attempts: Union[int, Sequence[RecoveryAttempt]] = 0,
        reference_time: Optional[datetime] = None,
    ) -> RiskAssessment:
        """Assess risk and recoverability for a failed payment.

        Can be called either with a Payment ORM instance or explicit parameters.
        """
        # Resolve error_code
        resolved_error_code = error_code
        if resolved_error_code is None and payment is not None:
            resolved_error_code = payment.error_code

        # Resolve reference_time
        resolved_ref_time = reference_time
        if resolved_ref_time is None and payment is not None and payment.created_at is not None:
            resolved_ref_time = payment.created_at
        if resolved_ref_time is None:
            resolved_ref_time = datetime.now(timezone.utc)
        elif resolved_ref_time.tzinfo is None:
            resolved_ref_time = resolved_ref_time.replace(tzinfo=timezone.utc)

        # Resolve previous attempts count
        if isinstance(previous_attempts, (list, tuple)):
            attempts_count = len(previous_attempts)
        else:
            attempts_count = int(previous_attempts)

        # Resolve customer history & recent success
        success_rate = 0.0
        has_recent_success = False

        if isinstance(customer_history, CustomerPaymentHistory):
            success_rate = customer_history.success_rate
            has_recent_success = customer_history.has_recent_success_in_30_days
        elif isinstance(customer_history, (list, tuple)):
            current_id = payment.id if payment is not None else None
            past_payments = [p for p in customer_history if current_id is None or p.id != current_id]
            if past_payments:
                successful_payments: List[Payment] = []
                for p in past_payments:
                    p_status = (p.status or "").strip().upper()
                    if p_status in {"SUCCESS", "SUCCEEDED", "PAID", "RECOVERED"}:
                        successful_payments.append(p)
                        if p.created_at is not None:
                            p_created = p.created_at
                            if p_created.tzinfo is None:
                                p_created = p_created.replace(tzinfo=timezone.utc)
                            delta = (resolved_ref_time - p_created).total_seconds()
                            if 0 <= delta <= 30 * 86400:
                                has_recent_success = True
                success_rate = (len(successful_payments) / len(past_payments)) * 100.0
        elif payment is not None and payment.customer is not None and payment.customer.payments:
            # Fallback to relationship if available on payment.customer
            all_payments = payment.customer.payments
            past_payments = [p for p in all_payments if p.id != payment.id]
            if past_payments:
                successful_payments = []
                for p in past_payments:
                    p_status = (p.status or "").strip().upper()
                    if p_status in {"SUCCESS", "SUCCEEDED", "PAID", "RECOVERED"}:
                        successful_payments.append(p)
                        if p.created_at is not None:
                            p_created = p.created_at
                            if p_created.tzinfo is None:
                                p_created = p_created.replace(tzinfo=timezone.utc)
                            delta = (resolved_ref_time - p_created).total_seconds()
                            if 0 <= delta <= 30 * 86400:
                                has_recent_success = True
                success_rate = (len(successful_payments) / len(past_payments)) * 100.0

        # Calculate scores
        history_score = cls.calculate_history_score(success_rate)
        recent_success_score = 20 if has_recent_success else 0
        failure_type_score = cls.calculate_failure_type_score(resolved_error_code)
        attempts_score = cls.calculate_attempts_score(attempts_count)

        raw_score = history_score + recent_success_score + failure_type_score + attempts_score
        risk_score = min(100, max(0, raw_score))

        failure_category = cls.classify_failure_category(resolved_error_code)
        recoverability = cls.calculate_recoverability(risk_score)

        breakdown = {
            "history_score": history_score,
            "recent_success_score": recent_success_score,
            "failure_type_score": failure_type_score,
            "attempts_score": attempts_score,
            "raw_total": raw_score,
        }

        # Build explainable human-readable reason
        reasons: List[str] = [
            f"Risk score: {risk_score}/100 ({recoverability.value}).",
            f"Customer history: success rate {success_rate:.1f}% (+{history_score}).",
            f"Recent success in 30d: {'Yes (+20)' if has_recent_success else 'No (+0)'}.",
            f"Failure error '{resolved_error_code or 'UNKNOWN'}': category {failure_category.value} (+{failure_type_score}).",
            f"Previous attempts ({attempts_count}): (+{attempts_score}).",
        ]
        reason_text = " ".join(reasons)

        return RiskAssessment(
            risk_score=risk_score,
            recoverability=recoverability,
            failure_category=failure_category,
            reason=reason_text,
            breakdown=breakdown,
        )
