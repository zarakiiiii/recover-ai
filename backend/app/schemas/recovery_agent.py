from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.policy import PolicyEvaluation
from app.schemas.risk import RiskAssessment


class RecoveryChannel(str, Enum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    EMAIL = "EMAIL"
    NONE = "NONE"


class RecoveryAgentAction(str, Enum):
    PAYMENT_LINK = "PAYMENT_LINK"
    NONE = "NONE"


class PaymentContext(BaseModel):
    """Context summary for the failed payment."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    amount_in_paise: int = Field(..., ge=0)
    currency: str = "INR"
    status: str = "FAILED"
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    gateway: Optional[str] = None


class CustomerContext(BaseModel):
    """Context summary for the customer."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    name: str
    email: str
    phone: Optional[str] = None
    total_payments: int = Field(default=0, ge=0)
    successful_payments: int = Field(default=0, ge=0)
    has_recent_success_in_30_days: bool = False


class RecoveryAgentContext(BaseModel):
    """Structured context passed into the RecoveryAgent."""
    payment: PaymentContext
    customer: CustomerContext
    risk_assessment: RiskAssessment
    policy_evaluation: PolicyEvaluation
    previous_attempts_count: int = Field(default=0, ge=0)


class RecoveryRecommendation(BaseModel):
    """Structured recovery recommendation produced by the AI Recovery Agent."""
    recommended_channel: RecoveryChannel = Field(
        ...,
        description="Recommended channel for customer communication: WHATSAPP, SMS, EMAIL, or NONE",
    )
    recommended_action: RecoveryAgentAction = Field(
        ...,
        description="Recommended recovery action: PAYMENT_LINK or NONE (must adhere to policy decision)",
    )
    explanation: str = Field(
        ...,
        description="Explanation for the recommendation based strictly on the supplied context",
    )
    customer_message: Optional[str] = Field(
        default=None,
        description="Customer-facing communication message. Must not expose internal risk scores or policy rules.",
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score in the recommendation (0.0 to 1.0)",
    )
    requires_human_review: bool = Field(
        default=False,
        description="Flag indicating whether human review is required before acting",
    )
