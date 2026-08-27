"""Deterministic synthetic data generator and database seeder for RecoverAI.

Generates ~50 customers and ~150 payments (approx 100 SUCCESS, 50 FAILED),
evaluates candidates using RiskEngine and PolicyEngine, and populates PostgreSQL.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import random
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import SessionLocal, engine
from app.models import (
    AuditEvent,
    Customer,
    FailureCategory,
    Payment,
    PolicyAction,
    PolicyDecision,
    Recoverability,
    RecoveryAction,
    RecoveryAttempt,
    RecoveryAttemptStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.risk import CustomerPaymentHistory
from app.services.policy_engine import PolicyEngine
from app.services.risk_engine import RiskEngine

logger = logging.getLogger("recoverai.seed")

# First and last names for generating realistic synthetic customers
FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Priya", "Vikram", "Ananya", "Rahul", "Neha",
    "Arjun", "Kavya", "Suresh", "Divya", "Amit", "Pooja", "Siddharth", "Meera",
    "Rajesh", "Sneha", "Varun", "Shreya", "Karthik", "Ritu", "Deepak", "Tanvi",
    "Gaurav", "Ishaan", "Riya", "Aditya", "Swati", "Nikhil", "Akash", "Pooja",
    "Manish", "Bhavna", "Karan", "Simran", "Alok", "Rashmi", "Sameer", "Tara",
    "Abhishek", "Sunita", "Harsh", "Deepika", "Mohit", "Preeti", "Sanjay", "Ankita",
    "Vishal", "Pallavi",
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Iyer", "Gupta", "Rao", "Reddy", "Nair",
    "Singh", "Joshi", "Mehta", "Kumar", "Das", "Agarwal", "Bhat", "Chopra",
    "Kapoor", "Banerjee", "Malhotra", "Saxena", "Choudhury", "Pillai", "Mishra", "Pandey",
]

FAILURE_TYPES = [
    "NETWORK_ERROR",
    "BANK_ERROR",
    "CARD_DECLINED",
    "EXPIRED_CARD",
    "INSUFFICIENT_FUNDS",
    "AUTHENTICATION_FAILED",
    "UNKNOWN_ERROR",
]

ERROR_DESCRIPTIONS = {
    "NETWORK_ERROR": "Connection timed out during payment gateway handshake.",
    "BANK_ERROR": "Issuing bank temporarily unavailable or declined the transaction.",
    "CARD_DECLINED": "Card issuer declined transaction due to card-level restriction.",
    "EXPIRED_CARD": "Card expiry date has passed.",
    "INSUFFICIENT_FUNDS": "Insufficient account balance to cover transaction.",
    "AUTHENTICATION_FAILED": "3D Secure OTP verification failed or was cancelled.",
    "UNKNOWN_ERROR": "Unspecified gateway processing anomaly.",
}


@dataclass
class GeneratedDataset:
    """In-memory dataset container for inspection and testing."""
    customers: List[Customer] = field(default_factory=list)
    payments: List[Payment] = field(default_factory=list)
    recovery_cases: List[RecoveryCase] = field(default_factory=list)
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)
    audit_events: List[AuditEvent] = field(default_factory=list)
    edge_cases_metadata: Dict[str, uuid.UUID] = field(default_factory=dict)


def generate_synthetic_dataset(seed: int = 42, base_time: Optional[datetime] = None) -> GeneratedDataset:
    """Deterministically generate synthetic customers, payments, and recovery cases."""
    rng = random.Random(seed)
    ref_time = base_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    dataset = GeneratedDataset()

    # Pre-generate 50 unique customers
    customer_profiles: List[Tuple[str, str, str, str]] = []  # (name, email, phone, profile_type)
    for i in range(50):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 3 + 7) % len(LAST_NAMES)]
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i+1}@example.in"
        phone = f"+9198{rng.randint(10000000, 99999999)}"

        if i < 18:
            profile = "HIGHLY_RELIABLE"  # ~18 customers, >=80% success
        elif i < 32:
            profile = "MODERATELY_RELIABLE"  # ~14 customers, 50-79% success
        elif i < 42:
            profile = "UNRELIABLE"  # ~10 customers, <50% success
        else:
            profile = "NEW_CUSTOMER"  # ~8 customers, 1-2 payments

        customer_profiles.append((name, email, phone, profile))

    # Create Customer models
    for name, email, phone, _ in customer_profiles:
        created_at = ref_time - timedelta(days=rng.randint(45, 90))
        cust = Customer(
            id=uuid.uuid4(),
            name=name,
            email=email,
            phone=phone,
            created_at=created_at,
            updated_at=created_at,
        )
        dataset.customers.append(cust)

    # Edge cases assignment to specific customer indices:
    # 0: Edge Case 1 (APPROVED: low value, high recoverability, NETWORK_ERROR, 0 attempts)
    # 1: Edge Case 2 (HUMAN_REVIEW: high value > ₹25k, BANK_ERROR)
    # 20: Edge Case 3 (STOP/BLOCKED: >=3 previous attempts, CARD_DECLINED)
    # 35: Edge Case 4 (BLOCKED: AUTHENTICATION_FAILED)
    # 45: Edge Case 5 (HUMAN_REVIEW: UNKNOWN_ERROR, uncertain failure)

    # Failure error pool for regular failed payments
    regular_failures = [
        "NETWORK_ERROR", "BANK_ERROR", "CARD_DECLINED", "EXPIRED_CARD",
        "INSUFFICIENT_FUNDS", "NETWORK_ERROR", "BANK_ERROR", "CARD_DECLINED",
        "INSUFFICIENT_FUNDS", "EXPIRED_CARD", "AUTHENTICATION_FAILED",
    ]
    reg_fail_idx = 0

    for idx, (cust, (_, _, _, profile)) in enumerate(zip(dataset.customers, customer_profiles)):
        customer_past_payments: List[Payment] = []

        # Determine number of payments and failure distribution based on profile
        if profile == "HIGHLY_RELIABLE":
            # 18 customers: 12 have 1 recent failure + 3 successes (4 total); 6 have 4 successes (4 total)
            # Total: 12 failures, 60 successes = 72 payments
            total_pmts = 4
            fail_count = 1 if idx < 12 else 0
        elif profile == "MODERATELY_RELIABLE":
            # 14 customers: each has 1 failure + 2 successes (3 total)
            # Total: 14 failures, 28 successes = 42 payments
            total_pmts = 3
            fail_count = 1
        elif profile == "UNRELIABLE":
            # 10 customers: each has 2 failures + 1 success (3 total)
            # Total: 20 failures, 10 successes = 30 payments
            total_pmts = 3
            fail_count = 2
        else:  # NEW_CUSTOMER
            # 8 customers: 4 have 1 failure + 1 success (2 total); 4 have 1 success (1 total)
            # Total: 4 failures, 8 successes = 12 payments
            if idx < 46:
                total_pmts = 2
                fail_count = 1
            else:
                total_pmts = 1
                fail_count = 0

        success_count = total_pmts - fail_count

        # Build successful prior payments
        for s_idx in range(success_count):
            days_ago = rng.randint(5, 35)
            pmt_time = ref_time - timedelta(days=days_ago, hours=rng.randint(1, 23))
            amount_paise = rng.choice([49900, 99900, 149900, 249900, 499900, 899900])  # ₹499 to ₹8,999

            p = Payment(
                id=uuid.uuid4(),
                customer_id=cust.id,
                amount_in_paise=amount_paise,
                currency="INR",
                status="SUCCESS",
                gateway="razorpay",
                gateway_payment_id=f"pay_succ_{rng.randint(100000, 999999)}",
                error_code=None,
                error_description=None,
                created_at=pmt_time,
                updated_at=pmt_time,
            )
            customer_past_payments.append(p)
            dataset.payments.append(p)

        # Build failed payments
        for f_idx in range(fail_count):
            days_ago = rng.randint(0, 5)
            pmt_time = ref_time - timedelta(days=days_ago, hours=rng.randint(0, 12))

            # Default payment attributes
            amount_paise = rng.choice([79900, 129900, 199900, 299900, 599900, 1299900])
            error_code = regular_failures[reg_fail_idx % len(regular_failures)]
            reg_fail_idx += 1
            num_attempts = 0

            # Override for deliberate edge cases
            if idx == 0 and f_idx == 0:
                # Edge Case 1: High recoverability, low value, NETWORK_ERROR, APPROVED
                amount_paise = 180000  # ₹1,800
                error_code = "NETWORK_ERROR"
                num_attempts = 0
                dataset.edge_cases_metadata["APPROVED_EDGE_CASE"] = None  # Will be set to pmt.id
            elif idx == 1 and f_idx == 0:
                # Edge Case 2: High value > ₹25,000, HUMAN_REVIEW
                amount_paise = 4200000  # ₹42,000 (4,200,000 paise)
                error_code = "BANK_ERROR"
                num_attempts = 0
                dataset.edge_cases_metadata["HIGH_VALUE_EDGE_CASE"] = None
            elif idx == 20 and f_idx == 0:
                # Edge Case 3: >= 3 previous attempts, STOP
                amount_paise = 250000  # ₹2,500
                error_code = "CARD_DECLINED"
                num_attempts = 3
                dataset.edge_cases_metadata["MAX_ATTEMPTS_STOP_EDGE_CASE"] = None
            elif idx == 35 and f_idx == 0:
                # Edge Case 4: AUTHENTICATION_FAILED, BLOCKED
                amount_paise = 320000  # ₹3,200
                error_code = "AUTHENTICATION_FAILED"
                num_attempts = 0
                dataset.edge_cases_metadata["AUTH_FAILED_EDGE_CASE"] = None
            elif idx == 45 and f_idx == 0:
                # Edge Case 5: Uncertain/Unknown error, HUMAN_REVIEW
                amount_paise = 450000  # ₹4,500
                error_code = "UNKNOWN_ERROR"
                num_attempts = 0
                dataset.edge_cases_metadata["UNKNOWN_ERROR_EDGE_CASE"] = None

            failed_payment = Payment(
                id=uuid.uuid4(),
                customer_id=cust.id,
                amount_in_paise=amount_paise,
                currency="INR",
                status="FAILED",
                gateway="razorpay",
                gateway_payment_id=f"pay_fail_{rng.randint(100000, 999999)}",
                error_code=error_code,
                error_description=ERROR_DESCRIPTIONS.get(error_code, "Payment transaction failed."),
                created_at=pmt_time,
                updated_at=pmt_time,
            )

            # Record edge case IDs
            if idx == 0 and f_idx == 0:
                dataset.edge_cases_metadata["APPROVED_EDGE_CASE"] = failed_payment.id
            elif idx == 1 and f_idx == 0:
                dataset.edge_cases_metadata["HIGH_VALUE_EDGE_CASE"] = failed_payment.id
            elif idx == 20 and f_idx == 0:
                dataset.edge_cases_metadata["MAX_ATTEMPTS_STOP_EDGE_CASE"] = failed_payment.id
            elif idx == 35 and f_idx == 0:
                dataset.edge_cases_metadata["AUTH_FAILED_EDGE_CASE"] = failed_payment.id
            elif idx == 45 and f_idx == 0:
                dataset.edge_cases_metadata["UNKNOWN_ERROR_EDGE_CASE"] = failed_payment.id

            dataset.payments.append(failed_payment)

            # Evaluate Risk and Policy using existing engines
            risk_assessment = RiskEngine.assess_risk(
                payment=failed_payment,
                customer_history=customer_past_payments,
                previous_attempts=num_attempts,
                reference_time=pmt_time,
            )

            policy_eval = PolicyEngine.evaluate_policy(
                risk_assessment=risk_assessment,
                payment=failed_payment,
                previous_attempts=num_attempts,
            )

            # Map to RecoveryCaseStatus
            if num_attempts >= 3:
                case_status = RecoveryCaseStatus.STOPPED
            elif policy_eval.decision == PolicyDecision.APPROVED:
                case_status = RecoveryCaseStatus.POLICY_REVIEW
            elif policy_eval.decision == PolicyDecision.HUMAN_REVIEW:
                case_status = RecoveryCaseStatus.HUMAN_REVIEW
            else:
                case_status = RecoveryCaseStatus.FAILED

            recovery_case = RecoveryCase(
                id=uuid.uuid4(),
                payment_id=failed_payment.id,
                status=case_status,
                policy_decision=policy_eval.decision,
                policy_reason=policy_eval.reason,
                created_at=pmt_time,
                updated_at=pmt_time,
            )
            dataset.recovery_cases.append(recovery_case)

            # Create previous recovery attempt records if attempts > 0
            for att_num in range(1, num_attempts + 1):
                att_time = pmt_time - timedelta(hours=(num_attempts - att_num + 1) * 4)
                attempt = RecoveryAttempt(
                    id=uuid.uuid4(),
                    recovery_case_id=recovery_case.id,
                    attempt_number=att_num,
                    action=RecoveryAction.PAYMENT_LINK,
                    status=RecoveryAttemptStatus.FAILED,
                    channel="WHATSAPP" if att_num % 2 == 1 else "SMS",
                    details={
                        "attempt": att_num,
                        "failure_reason": "Payment link expired or customer unopened",
                    },
                    created_at=att_time,
                    updated_at=att_time,
                )
                dataset.recovery_attempts.append(attempt)

            # Create initial AuditEvents
            audit_created = AuditEvent(
                id=uuid.uuid4(),
                recovery_case_id=recovery_case.id,
                event_type="PAYMENT_FAILED_INGESTED",
                from_state=None,
                to_state="PAYMENT_FAILED",
                actor="SYSTEM",
                payload={
                    "payment_id": str(failed_payment.id),
                    "amount_in_paise": failed_payment.amount_in_paise,
                    "error_code": failed_payment.error_code,
                },
                created_at=pmt_time,
            )
            audit_policy = AuditEvent(
                id=uuid.uuid4(),
                recovery_case_id=recovery_case.id,
                event_type="POLICY_EVALUATED",
                from_state="ANALYZING",
                to_state=case_status.value,
                actor="POLICY_ENGINE",
                payload={
                    "risk_score": risk_assessment.risk_score,
                    "recoverability": risk_assessment.recoverability.value,
                    "failure_category": risk_assessment.failure_category.value,
                    "decision": policy_eval.decision.value,
                    "allowed_action": policy_eval.allowed_action.value,
                    "reason": policy_eval.reason,
                },
                created_at=pmt_time + timedelta(seconds=2),
            )
            dataset.audit_events.extend([audit_created, audit_policy])

    return dataset


def seed_database(db: Session, reset: bool = False, seed: int = 42) -> GeneratedDataset:
    """Populate database with synthetic dataset. If reset=True, clears existing records first."""
    init_db()

    if reset:
        logger.info("Resetting existing database records...")
        db.execute(delete(AuditEvent))
        db.execute(delete(RecoveryAttempt))
        db.execute(delete(RecoveryCase))
        db.execute(delete(Payment))
        db.execute(delete(Customer))
        db.commit()

    # Generate dataset
    dataset = generate_synthetic_dataset(seed=seed)

    # Insert into database in relational order
    logger.info(f"Seeding {len(dataset.customers)} customers...")
    db.add_all(dataset.customers)
    db.flush()

    logger.info(f"Seeding {len(dataset.payments)} payments...")
    db.add_all(dataset.payments)
    db.flush()

    logger.info(f"Seeding {len(dataset.recovery_cases)} recovery cases...")
    db.add_all(dataset.recovery_cases)
    db.flush()

    if dataset.recovery_attempts:
        logger.info(f"Seeding {len(dataset.recovery_attempts)} recovery attempts...")
        db.add_all(dataset.recovery_attempts)
        db.flush()

    if dataset.audit_events:
        logger.info(f"Seeding {len(dataset.audit_events)} audit events...")
        db.add_all(dataset.audit_events)
        db.flush()

    db.commit()
    logger.info("Database seeding completed successfully.")
    return dataset


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed RecoverAI database with synthetic payments data.")
    parser.add_argument("--reset", action="store_true", help="Clear existing data before seeding")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    with SessionLocal() as session:
        data = seed_database(session, reset=args.reset, seed=args.seed)

        # Print summary statistics
        total_cust = len(data.customers)
        total_pmt = len(data.payments)
        succ_pmt = sum(1 for p in data.payments if p.status == "SUCCESS")
        fail_pmt = sum(1 for p in data.payments if p.status == "FAILED")
        print("\n--- Seeding Summary ---")
        print(f"Customers created: {total_cust}")
        print(f"Payments created: {total_pmt} (SUCCESS: {succ_pmt}, FAILED: {fail_pmt})")
        print(f"Recovery Cases created: {len(data.recovery_cases)}")
        print(f"Recovery Attempts created: {len(data.recovery_attempts)}")
        print(f"Audit Events created: {len(data.audit_events)}")
