from datetime import datetime, timezone
import pytest

from app.db.seed import generate_synthetic_dataset
from app.models.enums import (
    FailureCategory,
    PolicyAction,
    PolicyDecision,
    Recoverability,
    RecoveryCaseStatus,
)


def test_dataset_quantities_and_proportions():
    """Verify customer and payment counts adhere to milestone specifications (~50 customers, ~150 payments, ~100 success, ~50 failed)."""
    dataset = generate_synthetic_dataset(seed=42)

    assert len(dataset.customers) == 50
    assert len(dataset.payments) >= 140 and len(dataset.payments) <= 160

    successful_payments = [p for p in dataset.payments if p.status == "SUCCESS"]
    failed_payments = [p for p in dataset.payments if p.status == "FAILED"]

    assert len(successful_payments) >= 90 and len(successful_payments) <= 110
    assert len(failed_payments) >= 45 and len(failed_payments) <= 55
    assert len(dataset.recovery_cases) == len(failed_payments)


def test_dataset_deterministic_reproducibility():
    """Verify generator produces identical datasets when called with the same seed."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
    dataset_1 = generate_synthetic_dataset(seed=42, base_time=base_time)
    dataset_2 = generate_synthetic_dataset(seed=42, base_time=base_time)

    assert len(dataset_1.customers) == len(dataset_2.customers)
    assert len(dataset_1.payments) == len(dataset_2.payments)
    assert [p.amount_in_paise for p in dataset_1.payments] == [p.amount_in_paise for p in dataset_2.payments]
    assert [p.status for p in dataset_1.payments] == [p.status for p in dataset_2.payments]
    assert [p.error_code for p in dataset_1.payments] == [p.error_code for p in dataset_2.payments]


def test_all_failure_types_present():
    """Verify all required failure types and uncertain errors exist among failed payments."""
    dataset = generate_synthetic_dataset(seed=42)
    failed_payments = [p for p in dataset.payments if p.status == "FAILED"]
    error_codes = {p.error_code for p in failed_payments if p.error_code}

    required_types = {
        "NETWORK_ERROR",
        "BANK_ERROR",
        "CARD_DECLINED",
        "EXPIRED_CARD",
        "INSUFFICIENT_FUNDS",
        "AUTHENTICATION_FAILED",
        "UNKNOWN_ERROR",
    }

    assert required_types.issubset(error_codes)


def test_edge_case_1_high_recoverability_approved():
    """Edge Case 1: High recoverability low-value payment is APPROVED."""
    dataset = generate_synthetic_dataset(seed=42)
    pmt_id = dataset.edge_cases_metadata["APPROVED_EDGE_CASE"]
    pmt = next(p for p in dataset.payments if p.id == pmt_id)
    case = next(c for c in dataset.recovery_cases if c.payment_id == pmt_id)

    assert pmt.status == "FAILED"
    assert pmt.amount_in_paise <= 2_500_000  # <= ₹25,000
    assert pmt.error_code in {"NETWORK_ERROR", "BANK_ERROR"}
    assert case.policy_decision == PolicyDecision.APPROVED


def test_edge_case_2_high_value_human_review():
    """Edge Case 2: High value transaction (> ₹25,000) requires HUMAN_REVIEW."""
    dataset = generate_synthetic_dataset(seed=42)
    pmt_id = dataset.edge_cases_metadata["HIGH_VALUE_EDGE_CASE"]
    pmt = next(p for p in dataset.payments if p.id == pmt_id)
    case = next(c for c in dataset.recovery_cases if c.payment_id == pmt_id)

    assert pmt.status == "FAILED"
    assert pmt.amount_in_paise > 2_500_000  # > ₹25,000
    assert case.policy_decision == PolicyDecision.HUMAN_REVIEW
    assert "exceeds" in case.policy_reason.lower()


def test_edge_case_3_max_attempts_stops_recovery():
    """Edge Case 3: Payment with >= 3 previous recovery attempts triggers STOP / BLOCKED."""
    dataset = generate_synthetic_dataset(seed=42)
    pmt_id = dataset.edge_cases_metadata["MAX_ATTEMPTS_STOP_EDGE_CASE"]
    pmt = next(p for p in dataset.payments if p.id == pmt_id)
    case = next(c for c in dataset.recovery_cases if c.payment_id == pmt_id)

    attempts = [a for a in dataset.recovery_attempts if a.recovery_case_id == case.id]

    assert len(attempts) >= 3
    assert case.status == RecoveryCaseStatus.STOPPED
    assert case.policy_decision == PolicyDecision.BLOCKED
    assert "STOP" in case.policy_reason


def test_edge_case_4_authentication_failed_blocked():
    """Edge Case 4: AUTHENTICATION_FAILED payment is BLOCKED (NON_RECOVERABLE)."""
    dataset = generate_synthetic_dataset(seed=42)
    pmt_id = dataset.edge_cases_metadata["AUTH_FAILED_EDGE_CASE"]
    pmt = next(p for p in dataset.payments if p.id == pmt_id)
    case = next(c for c in dataset.recovery_cases if c.payment_id == pmt_id)

    assert pmt.error_code == "AUTHENTICATION_FAILED"
    assert case.policy_decision == PolicyDecision.BLOCKED
    assert "NON_RECOVERABLE" in case.policy_reason


def test_edge_case_5_uncertain_failure_human_review():
    """Edge Case 5: Unknown/uncertain failure type triggers HUMAN_REVIEW."""
    dataset = generate_synthetic_dataset(seed=42)
    pmt_id = dataset.edge_cases_metadata["UNKNOWN_ERROR_EDGE_CASE"]
    pmt = next(p for p in dataset.payments if p.id == pmt_id)
    case = next(c for c in dataset.recovery_cases if c.payment_id == pmt_id)

    assert pmt.error_code == "UNKNOWN_ERROR"
    assert case.policy_decision == PolicyDecision.HUMAN_REVIEW
