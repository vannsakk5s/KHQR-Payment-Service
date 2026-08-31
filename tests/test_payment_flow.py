from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.core.config import get_settings
from app.services.khqr import MockKhqrProvider, get_khqr_provider


def get_auth_headers():
    return {"X-Internal-API-Key": get_settings().internal_api_key}


def test_create_and_mock_pay(monkeypatch):
    # Ensure mock provider is used for this unit test
    mock_provider = MockKhqrProvider()
    monkeypatch.setattr("app.api.routes.payments.get_khqr_provider", lambda: mock_provider)

    with TestClient(app) as client:
        headers = get_auth_headers()
        request = {
            "booking_id": 2,
            "customer_id": 6,
            "amount": "30.00",
            "currency": "USD",
            "payment_type": "DEPOSIT",
            "payment_method": "KHQR",
            "idempotency_key": "booking-2-deposit-v1-mock-test",
        }

        created = client.post("/api/v1/payments", json=request, headers=headers)
        assert created.status_code == 201
        payment = created.json()
        assert payment["booking_id"] == 2
        assert payment["status"] == "PENDING"
        assert payment["qr_payload"].startswith("MOCK-KHQR")

        duplicate = client.post("/api/v1/payments", json=request, headers=headers)
        assert duplicate.status_code == 201
        assert duplicate.json()["id"] == payment["id"]

        paid = client.post(
            f'/api/v1/payments/{payment["id"]}/mock-paid', headers=headers
        )
        assert paid.status_code == 200
        assert paid.json()["payment"]["status"] == "PAID"


def test_requires_internal_api_key():
    with TestClient(app) as client:
        # Missing header
        response = client.get("/api/v1/payments/not-found")
        assert response.status_code == 422

        # Invalid header
        response_invalid = client.get(
            "/api/v1/payments/not-found",
            headers={"X-Internal-API-Key": "invalid-wrong-key"},
        )
        assert response_invalid.status_code == 401

