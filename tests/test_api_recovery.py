import uuid
from fastapi.testclient import TestClient
import pytest

from app.db.seed import seed_database
from app.db.session import SessionLocal
from app.main import app
from app.models import RecoveryCase

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
