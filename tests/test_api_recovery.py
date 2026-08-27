import uuid
from fastapi.testclient import TestClient
import pytest

from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.main import app
from app.models import AuditEvent, PolicyDecision, RecoveryAttempt, RecoveryCase, RecoveryCaseStatus

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database has deterministic seeded data for API tests."""
    with SessionLocal() as db:
        seed_database(db, reset=True, seed=42)
    yield


def test_get_recovery_overview():
    """Verify GET /api/recovery/overview returns dynamically calculated metrics from PostgreSQL."""
    response = client.get("/api/recovery/overview")
    assert response.status_code == 200

    data = response.json()
    assert "total_failed_payments" in data
    assert "total_revenue_at_risk_in_paise" in data
    assert "approved_cases" in data
    assert "human_review_cases" in data
    assert "blocked_cases" in data
    assert "stopped_cases" in data
    assert "total_recovery_attempts" in data

    # Verify realistic non-zero calculated values from seeded dataset
    assert data["total_failed_payments"] == 50
    assert data["total_revenue_at_risk_in_paise"] > 0
    assert data["approved_cases"] == 15
    assert data["human_review_cases"] == 30
    assert data["blocked_cases"] == 5
    assert data["stopped_cases"] == 1
    assert data["total_recovery_attempts"] == 3


def test_get_recovery_candidates():
    """Verify GET /api/recovery/candidates returns all APPROVED recovery candidates."""
    response = client.get("/api/recovery/candidates")
    assert response.status_code == 200

    candidates = response.json()
    assert isinstance(candidates, list)
    assert len(candidates) == 15  # Exactly 15 approved cases

    for candidate in candidates:
        assert candidate["policy_decision"] == "APPROVED"
        assert candidate["allowed_action"] == "PAYMENT_LINK"
        assert candidate["customer_name"]
        assert candidate["amount_in_paise"] > 0
        assert candidate["currency"] == "INR"
        assert "recovery_case_id" in candidate
        assert "payment_id" in candidate


def test_get_recovery_case_detail_success():
    """Verify GET /api/recovery/cases/{case_id} returns comprehensive case details."""
    with SessionLocal() as db:
        case = db.query(RecoveryCase).first()
        assert case is not None
        case_id = str(case.id)

    response = client.get(f"/api/recovery/cases/{case_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == case_id
    assert "status" in data
    assert "payment" in data
    assert "customer" in data
    assert "recovery_attempts" in data
    assert "audit_events" in data

    # Verify nested payment structure
    payment = data["payment"]
    assert payment["amount_in_paise"] > 0
    assert payment["status"] == "FAILED"

    # Verify nested customer structure
    customer = data["customer"]
    assert customer["name"]
    assert customer["email"]


def test_get_recovery_case_detail_stopped_with_attempts():
    """Verify case detail for stopped case contains the 3 previous recovery attempts."""
    with SessionLocal() as db:
        case = db.query(RecoveryCase).filter(RecoveryCase.status == "STOPPED").first()
        assert case is not None
        case_id = str(case.id)

    response = client.get(f"/api/recovery/cases/{case_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "STOPPED"
    assert len(data["recovery_attempts"]) == 3
    assert len(data["audit_events"]) >= 2


def test_get_recovery_case_detail_404_not_found():
    """Verify GET /api/recovery/cases/{case_id} returns 404 for non-existent case ID."""
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/recovery/cases/{random_uuid}")
    assert response.status_code == 404
    assert f"'{random_uuid}' was not found" in response.json()["detail"]


def test_execute_approved_case_success():
    """Verify POST /api/recovery/cases/{case_id}/execute successfully executes an APPROVED case."""
    with SessionLocal() as db:
        approved_case = db.query(RecoveryCase).filter(RecoveryCase.policy_decision == PolicyDecision.APPROVED).first()
        assert approved_case is not None
        case_id = str(approved_case.id)

    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 200

    data = response.json()
    assert data["recovery_case_id"] == case_id
    assert "attempt_id" in data
    assert data["attempt_number"] >= 1
    assert data["status"] == "SUCCESS"
    assert data["action"] == "PAYMENT_LINK"
    assert data["channel"] in {"WHATSAPP", "SMS", "EMAIL"}
    assert "https://pay.recoverai.internal/mock/" in data["payment_link"]
    assert data["payment_link"] in data["message"]

    # Verify message does not leak internal terms
    forbidden_terms = ["risk_score", "policy_engine", "algorithm", "paise"]
    for term in forbidden_terms:
        assert term not in data["message"].lower()

    # Verify database state updates
    with SessionLocal() as db:
        updated_case = db.query(RecoveryCase).filter(RecoveryCase.id == uuid.UUID(case_id)).first()
        assert updated_case.status == RecoveryCaseStatus.RECOVERED

        # Verify attempt record
        attempt = db.query(RecoveryAttempt).filter(RecoveryAttempt.id == uuid.UUID(data["attempt_id"])).first()
        assert attempt is not None
        assert attempt.details["mock_execution"] is True

        # Verify audit events persisted
        audit_events = db.query(AuditEvent).filter(AuditEvent.recovery_case_id == uuid.UUID(case_id)).all()
        event_types = {e.event_type for e in audit_events}
        assert "RECOVERY_EXECUTION_STARTED" in event_types
        assert "RECOVERY_EXECUTION_COMPLETED" in event_types


def test_execute_blocked_case_fails():
    """Verify executing a BLOCKED case is rejected with 400 Bad Request."""
    with SessionLocal() as db:
        blocked_case = db.query(RecoveryCase).filter(
            RecoveryCase.policy_decision == PolicyDecision.BLOCKED,
            RecoveryCase.status != RecoveryCaseStatus.STOPPED,
        ).first()
        assert blocked_case is not None
        case_id = str(blocked_case.id)

    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 400
    assert "not authorized" in response.json()["detail"].lower() or "blocked" in response.json()["detail"].lower()


def test_execute_human_review_case_fails():
    """Verify executing a HUMAN_REVIEW case is rejected with 400 Bad Request."""
    with SessionLocal() as db:
        review_case = db.query(RecoveryCase).filter(RecoveryCase.policy_decision == PolicyDecision.HUMAN_REVIEW).first()
        assert review_case is not None
        case_id = str(review_case.id)

    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 400
    assert "not authorized" in response.json()["detail"].lower()


def test_execute_stopped_case_fails():
    """Verify executing a STOPPED case is rejected with 400 Bad Request."""
    with SessionLocal() as db:
        stopped_case = db.query(RecoveryCase).filter(RecoveryCase.status == RecoveryCaseStatus.STOPPED).first()
        assert stopped_case is not None
        case_id = str(stopped_case.id)

    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 400
    assert "stopped" in response.json()["detail"].lower() or "maximum" in response.json()["detail"].lower()


def test_execute_case_404_not_found():
    """Verify executing non-existent case returns 404."""
    random_uuid = str(uuid.uuid4())
    response = client.post(f"/api/recovery/cases/{random_uuid}/execute")
    assert response.status_code == 404
