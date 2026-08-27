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


class Recoverability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FailureCategory(str, Enum):
    RECOVERABLE = "RECOVERABLE"
    UNCERTAIN = "UNCERTAIN"
    NON_RECOVERABLE = "NON_RECOVERABLE"


class PolicyAction(str, Enum):
    PAYMENT_LINK = "PAYMENT_LINK"
    NONE = "NONE"


class FailureType(str, Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    BANK_ERROR = "BANK_ERROR"
    CARD_DECLINED = "CARD_DECLINED"
    EXPIRED_CARD = "EXPIRED_CARD"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
