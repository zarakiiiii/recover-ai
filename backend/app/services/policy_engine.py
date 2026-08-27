from typing import Optional, Sequence, Union

from app.models.enums import FailureCategory, PolicyAction, PolicyDecision, Recoverability
from app.models.payment import Payment
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.policy import PolicyEvaluation
from app.schemas.risk import RiskAssessment

# Threshold for manual human review: > 25,000 INR (in paise: 25,000 * 100 = 2,500,000)
HIGH_VALUE_THRESHOLD_INR = 25_000
HIGH_VALUE_THRESHOLD_PAISE = HIGH_VALUE_THRESHOLD_INR * 100  # 2,500,000 paise
MAX_RECOVERY_ATTEMPTS = 3


class PolicyEngine:
    """Deterministic Policy Engine for automated recovery decisions."""

    @classmethod
    def evaluate_policy(
        cls,
        *,
        risk_assessment: RiskAssessment,
        payment: Optional[Payment] = None,
        amount_in_paise: Optional[int] = None,
        previous_attempts: Union[int, Sequence[RecoveryAttempt]] = 0,
    ) -> PolicyEvaluation:
        """Evaluate recovery policy rules sequentially and return decision, reason, and allowed action.

        Rules:
        1. If previous recovery attempts >= 3 -> STOP (BLOCKED, allowed_action: NONE)
        2. Else if payment amount > 25,000 INR -> HUMAN_REVIEW (allowed_action: NONE)
        3. Else if failure category is NON_RECOVERABLE -> BLOCKED (allowed_action: NONE)
        4. Else if recoverability is HIGH -> APPROVED (allowed_action: PAYMENT_LINK)
        5. Else -> HUMAN_REVIEW (allowed_action: NONE)
        """
        # Resolve attempts count
        if isinstance(previous_attempts, (list, tuple)):
            attempts_count = len(previous_attempts)
        else:
            attempts_count = int(previous_attempts)

        # Resolve amount in paise
        resolved_amount_paise = amount_in_paise
        if resolved_amount_paise is None and payment is not None:
            resolved_amount_paise = payment.amount_in_paise
        if resolved_amount_paise is None:
            resolved_amount_paise = 0

        amount_in_inr = resolved_amount_paise / 100.0

        # Rule 1: Max recovery attempts reached
        if attempts_count >= MAX_RECOVERY_ATTEMPTS:
            return PolicyEvaluation(
                decision=PolicyDecision.BLOCKED,
                reason=(
                    f"STOP: Previous recovery attempts ({attempts_count}) reached or exceeded limit of "
                    f"{MAX_RECOVERY_ATTEMPTS}. Further automated recovery is stopped."
                ),
                allowed_action=PolicyAction.NONE,
            )

        # Rule 2: High value transaction (> 25,000 INR)
        if resolved_amount_paise > HIGH_VALUE_THRESHOLD_PAISE:
            return PolicyEvaluation(
                decision=PolicyDecision.HUMAN_REVIEW,
                reason=(
                    f"Payment amount (INR {amount_in_inr:,.2f}) exceeds the automated recovery limit of "
                    f"INR {HIGH_VALUE_THRESHOLD_INR:,.2f}. Escalated to human review."
                ),
                allowed_action=PolicyAction.NONE,
            )

        # Rule 3: Non-recoverable failure category
        if risk_assessment.failure_category == FailureCategory.NON_RECOVERABLE:
            return PolicyEvaluation(
                decision=PolicyDecision.BLOCKED,
                reason=(
                    "Payment failure category is NON_RECOVERABLE (e.g., authentication failed). "
                    "Automated recovery is blocked."
                ),
                allowed_action=PolicyAction.NONE,
            )

        # Rule 4: High recoverability
        if risk_assessment.recoverability == Recoverability.HIGH:
            return PolicyEvaluation(
                decision=PolicyDecision.APPROVED,
                reason=(
                    f"High recoverability assessment (score: {risk_assessment.risk_score}/100). "
                    "Automated payment link recovery is approved."
                ),
                allowed_action=PolicyAction.PAYMENT_LINK,
            )

        # Rule 5: Fallback (Moderate or Low recoverability)
        return PolicyEvaluation(
            decision=PolicyDecision.HUMAN_REVIEW,
            reason=(
                f"Recoverability is {risk_assessment.recoverability.value} "
                f"(score: {risk_assessment.risk_score}/100, category: {risk_assessment.failure_category.value}). "
                "Requires human review before initiating recovery action."
            ),
            allowed_action=PolicyAction.NONE,
        )
