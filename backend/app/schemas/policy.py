from pydantic import BaseModel, Field

from app.models.enums import PolicyAction, PolicyDecision


class PolicyEvaluation(BaseModel):
    """Deterministic policy evaluation result."""
    decision: PolicyDecision = Field(..., description="Policy decision: APPROVED, HUMAN_REVIEW, or BLOCKED")
    reason: str = Field(..., description="Human-readable justification for the policy decision")
    allowed_action: PolicyAction = Field(..., description="Allowed recovery action: PAYMENT_LINK or NONE")
