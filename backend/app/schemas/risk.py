from typing import Dict, Optional
from pydantic import BaseModel, Field

from app.models.enums import FailureCategory, Recoverability


class CustomerPaymentHistory(BaseModel):
    """Aggregated payment history for a customer."""
    total_payments: int = Field(default=0, ge=0)
    successful_payments: int = Field(default=0, ge=0)
    has_recent_success_in_30_days: bool = False

    @property
    def success_rate(self) -> float:
        if self.total_payments == 0:
            return 0.0
        return (self.successful_payments / self.total_payments) * 100.0


class RiskAssessment(BaseModel):
    """Deterministic risk assessment output."""
    risk_score: int = Field(..., ge=0, le=100, description="Risk/recoverability score between 0 and 100")
    recoverability: Recoverability = Field(..., description="Recoverability rating: HIGH, MEDIUM, or LOW")
    failure_category: FailureCategory = Field(..., description="Failure classification: RECOVERABLE, UNCERTAIN, or NON_RECOVERABLE")
    reason: str = Field(..., description="Human-readable explanation of the assessment")
    breakdown: Optional[Dict[str, int]] = Field(default=None, description="Detailed score component breakdown")
