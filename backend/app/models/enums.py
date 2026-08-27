from enum import Enum


class RecoveryCaseStatus(str, Enum):
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ANALYZING = "ANALYZING"
    POLICY_REVIEW = "POLICY_REVIEW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    EXECUTING = "EXECUTING"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class RecoveryAttemptStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PolicyDecision(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RecoveryAction(str, Enum):
    PAYMENT_LINK = "PAYMENT_LINK"
