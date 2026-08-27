from abc import ABC, abstractmethod
import json
import logging
from typing import Optional, Sequence, Union
import uuid

import httpx

from app.core.config import settings
from app.models import Customer, Payment, PolicyDecision, RecoveryAttempt
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

logger = logging.getLogger("recoverai.recovery_agent")

SYSTEM_PROMPT = (
    "You are RecoverAI's recovery assistant. Analyze the supplied payment, customer, "
    "risk, and policy context and recommend an appropriate recovery communication strategy. "
    "You may recommend actions only within the policy decision supplied to you. Never override policy.\n\n"
    "Explicit distinctions:\n"
    "- Deterministic Risk Assessment: Scored mathematically from customer and failure history.\n"
    "- Deterministic Policy Authorization: The final business decision (APPROVED, HUMAN_REVIEW, BLOCKED).\n"
    "- AI Recommendation: Selecting optimal channel (WHATSAPP, SMS, EMAIL, NONE), customer messaging, and review flags.\n\n"
    "Rules:\n"
    "1. If policy decision is BLOCKED or case is STOPPED -> recommended_action must be NONE and recommended_channel must be NONE.\n"
    "2. If policy decision is HUMAN_REVIEW -> requires_human_review must be true and recommended_action must be NONE.\n"
    "3. Only if policy decision is APPROVED may you recommend PAYMENT_LINK.\n"
    "4. Customer-facing messages must be courteous and must NEVER mention risk scores, internal metrics, or policy algorithms."
)


class BaseLLMClient(ABC):
    """Abstract interface for LLM provider clients."""

    @abstractmethod
    def generate(self, context: RecoveryAgentContext) -> RecoveryRecommendation:
        """Generate a structured RecoveryRecommendation from context."""
        pass


class MockLLMClient(BaseLLMClient):
    """Deterministic rule-based mock LLM client for local and offline execution."""

    def generate(self, context: RecoveryAgentContext) -> RecoveryRecommendation:
        decision = context.policy_evaluation.decision
        amount_inr = context.payment.amount_in_paise / 100.0
        cust_name = context.customer.name
        attempts = context.previous_attempts_count

        if attempts >= 3:
            return RecoveryRecommendation(
                recommended_channel=RecoveryChannel.NONE,
                recommended_action=RecoveryAgentAction.NONE,
                explanation=(
                    f"Recovery case is stopped because maximum retry limit ({attempts} attempts) has been reached. "
                    "No further automated communication is permitted."
                ),
                customer_message=None,
                confidence=1.0,
                requires_human_review=False,
            )

        if decision == PolicyDecision.APPROVED:
            # Select best channel: WhatsApp if phone available, otherwise Email
            channel = RecoveryChannel.WHATSAPP if context.customer.phone else RecoveryChannel.EMAIL

            message = (
                f"Hi {cust_name}, we noticed your recent payment of INR {amount_inr:,.2f} could not be completed "
                f"due to a temporary banking network issue. You can easily complete your payment here: {{{{payment_link}}}}. "
                f"Please let us know if you need any help!"
            )

            explanation = (
                f"Customer {cust_name} has high recoverability (score {context.risk_assessment.risk_score}/100) "
                f"and policy approval for amount INR {amount_inr:,.2f}. Recommending {channel.value} payment link retry."
            )

            return RecoveryRecommendation(
                recommended_channel=channel,
                recommended_action=RecoveryAgentAction.PAYMENT_LINK,
                explanation=explanation,
                customer_message=message,
                confidence=0.95,
                requires_human_review=False,
            )

        elif decision == PolicyDecision.HUMAN_REVIEW:
            return RecoveryRecommendation(
                recommended_channel=RecoveryChannel.NONE,
                recommended_action=RecoveryAgentAction.NONE,
                explanation=(
                    f"Case requires human review: {context.policy_evaluation.reason}. "
                    "Automated recovery action is held pending operator review."
                ),
                customer_message=None,
                confidence=0.90,
                requires_human_review=True,
            )

        else:  # BLOCKED
            return RecoveryRecommendation(
                recommended_channel=RecoveryChannel.NONE,
                recommended_action=RecoveryAgentAction.NONE,
                explanation=(
                    f"Automated recovery is blocked: {context.policy_evaluation.reason}. "
                    "No communication or payment link will be sent to the customer."
                ),
                customer_message=None,
                confidence=1.0,
                requires_human_review=False,
            )


class OpenAIGenericClient(BaseLLMClient):
    """Generic HTTP LLM client supporting OpenAI / Gemini compatible endpoints."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def generate(self, context: RecoveryAgentContext) -> RecoveryRecommendation:
        prompt_payload = {
            "payment": context.payment.model_dump(mode="json"),
            "customer": context.customer.model_dump(mode="json"),
            "risk_assessment": context.risk_assessment.model_dump(mode="json"),
            "policy_evaluation": context.policy_evaluation.model_dump(mode="json"),
            "previous_attempts_count": context.previous_attempts_count,
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Generate a recovery recommendation for the following context:\n\n"
                            f"{json.dumps(prompt_payload, indent=2)}\n\n"
                            f"Respond strictly in JSON matching the RecoveryRecommendation schema."
                        ),
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return RecoveryRecommendation.model_validate(parsed)
        except Exception as e:
            logger.warning(f"External LLM call failed ({e}). Falling back to MockLLMClient.")
            return MockLLMClient().generate(context)


class RecoveryAgent:
    """AI Recovery Agent with deterministic policy guardrails."""

    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or settings.AI_PROVIDER).lower()
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL

        # Initialize LLM client abstraction
        if self.provider == "mock" or not self.api_key:
            self.client: BaseLLMClient = MockLLMClient()
        else:
            self.client = OpenAIGenericClient(api_key=self.api_key, model=self.model)

    @classmethod
    def enforce_safety_guardrails(
        cls,
        context: RecoveryAgentContext,
        recommendation: RecoveryRecommendation,
    ) -> RecoveryRecommendation:
        """Enforce strict safety rules so AI never overrides policy authorization."""
        policy_decision = context.policy_evaluation.decision
        attempts = context.previous_attempts_count

        # Rule 1: STOPPED or attempts >= 3 -> Action MUST be NONE, Channel NONE, no message
        if attempts >= 3:
            recommendation.recommended_action = RecoveryAgentAction.NONE
            recommendation.recommended_channel = RecoveryChannel.NONE
            recommendation.customer_message = None
            recommendation.requires_human_review = False
            return recommendation

        # Rule 2: BLOCKED -> Action MUST be NONE, Channel NONE, no message
        if policy_decision == PolicyDecision.BLOCKED:
            recommendation.recommended_action = RecoveryAgentAction.NONE
            recommendation.recommended_channel = RecoveryChannel.NONE
            recommendation.customer_message = None
            recommendation.requires_human_review = False
            return recommendation

        # Rule 3: HUMAN_REVIEW -> requires_human_review MUST be True and Action MUST be NONE
        if policy_decision == PolicyDecision.HUMAN_REVIEW:
            recommendation.recommended_action = RecoveryAgentAction.NONE
            recommendation.requires_human_review = True
            recommendation.customer_message = None
            return recommendation

        # Rule 4: Only APPROVED cases may have automated PAYMENT_LINK
        if policy_decision != PolicyDecision.APPROVED:
            recommendation.recommended_action = RecoveryAgentAction.NONE

        # Rule 5: Safety filter to ensure internal risk/policy terms never leak to customer
        if recommendation.customer_message:
            forbidden_tokens = ["risk_score", "risk score", "policy_engine", "recoverability", "algorithm", "paise"]
            msg_lower = recommendation.customer_message.lower()
            if any(token in msg_lower for token in forbidden_tokens):
                amount_inr = context.payment.amount_in_paise / 100.0
                recommendation.customer_message = (
                    f"Hi {context.customer.name}, your payment of INR {amount_inr:,.2f} could not be completed. "
                    f"Please complete your payment securely here: {{{{payment_link}}}}."
                )

        return recommendation

    def generate_recommendation(self, context: RecoveryAgentContext) -> RecoveryRecommendation:
        """Generate a RecoveryRecommendation and pass it through policy safety guardrails."""
        # 1. Generate recommendation from LLM abstraction
        raw_recommendation = self.client.generate(context)

        # 2. Programmatically enforce policy guardrails
        safe_recommendation = self.enforce_safety_guardrails(context, raw_recommendation)
        return safe_recommendation

    def generate_from_models(
        self,
        *,
        payment: Payment,
        customer: Customer,
        risk_assessment: RiskAssessment,
        policy_evaluation: PolicyEvaluation,
        previous_attempts: Union[int, Sequence[RecoveryAttempt]] = 0,
    ) -> RecoveryRecommendation:
        """Helper to build context from ORM models and generate a recommendation."""
        if isinstance(previous_attempts, (list, tuple)):
            attempts_count = len(previous_attempts)
        else:
            attempts_count = int(previous_attempts)

        # Build CustomerContext
        total_p = len(customer.payments) if customer.payments else 0
        succ_p = sum(1 for p in customer.payments if p.status == "SUCCESS") if customer.payments else 0

        cust_ctx = CustomerContext(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            total_payments=total_p,
            successful_payments=succ_p,
        )

        pmt_ctx = PaymentContext(
            id=payment.id,
            amount_in_paise=payment.amount_in_paise,
            currency=payment.currency,
            status=payment.status,
            error_code=payment.error_code,
            error_description=payment.error_description,
            gateway=payment.gateway,
        )

        context = RecoveryAgentContext(
            payment=pmt_ctx,
            customer=cust_ctx,
            risk_assessment=risk_assessment,
            policy_evaluation=policy_evaluation,
            previous_attempts_count=attempts_count,
        )

        return self.generate_recommendation(context)
