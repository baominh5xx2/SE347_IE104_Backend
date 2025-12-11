"""
Unit tests for Admin Recommendations API
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.v1.api.endpoints import admin_recommendations


@pytest.fixture
def app_client():
    app = FastAPI()
    app.include_router(admin_recommendations.router, prefix="/api/v1/tour-packages")
    client = TestClient(app)
    return app, client


@pytest.fixture
def mock_service():
    service = MagicMock()
    return service


@pytest.fixture
def admin_user():
    return {"user_id": "admin-123", "role": "admin"}


def test_get_admin_recommendations(app_client, mock_service, admin_user):
    app, client = app_client

    # Mock dependencies
    app.dependency_overrides[admin_recommendations.get_tour_package_service] = lambda: mock_service
    app.dependency_overrides[admin_recommendations.check_admin_role] = lambda: admin_user

    # Mock service responses
    mock_service.get_admin_setting.return_value = True
    mock_service.get_featured_tours.return_value = [{"package_id": "111", "package_name": "Tour A"}]

    resp = client.get("/api/v1/tour-packages/admin/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["EC"] == 0
    assert body["data"]["enabled"] is True
    assert body["data"]["total_featured"] == 1
    mock_service.get_admin_setting.assert_called_once_with(
        "ADMIN_RECOMMENDATION_ENABLED", default_value=admin_recommendations.settings.ADMIN_RECOMMENDATION_ENABLED
    )
    mock_service.get_featured_tours.assert_called_once()


def test_put_admin_recommendations_updates_flag_and_featured(app_client, mock_service, admin_user):
    app, client = app_client

    # Mock dependencies
    app.dependency_overrides[admin_recommendations.get_tour_package_service] = lambda: mock_service
    app.dependency_overrides[admin_recommendations.check_admin_role] = lambda: admin_user

    # Mock service responses
    mock_service.set_admin_setting.return_value = True
    mock_service.update_featured_tours.return_value = {
        "success": True,
        "updated": 2,
        "valid_ids": ["111", "222"],
        "invalid_ids": []
    }
    mock_service.get_admin_setting.return_value = True
    mock_service.get_featured_tours.return_value = [
        {"package_id": "111", "package_name": "Tour A"},
        {"package_id": "222", "package_name": "Tour B"}
    ]

    payload = {
        "enabled": True,
        "tour_package_ids": ["111", "222"]
    }
    resp = client.put("/api/v1/tour-packages/admin/recommendations", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["EC"] == 0
    assert body["data"]["enabled"] is True
    assert body["data"]["total_featured"] == 2

    mock_service.set_admin_setting.assert_called_once_with(
        "ADMIN_RECOMMENDATION_ENABLED", True, updated_by="admin-123"
    )
    mock_service.update_featured_tours.assert_called_once_with(["111", "222"])
    assert mock_service.get_admin_setting.called
    assert mock_service.get_featured_tours.called


def test_put_admin_recommendations_handles_invalid_ids(app_client, mock_service, admin_user):
    app, client = app_client

    app.dependency_overrides[admin_recommendations.get_tour_package_service] = lambda: mock_service
    app.dependency_overrides[admin_recommendations.check_admin_role] = lambda: admin_user

    mock_service.set_admin_setting.return_value = True
    mock_service.update_featured_tours.return_value = {
        "success": False,
        "message": "No valid package IDs provided",
        "updated": 0
    }

    payload = {
        "enabled": True,
        "tour_package_ids": ["bad-id"]
    }
    resp = client.put("/api/v1/tour-packages/admin/recommendations", json=payload)
    assert resp.status_code == 400
    assert "Failed to update featured tours" in resp.text


def test_put_admin_recommendations_persist_fail(app_client, mock_service, admin_user):
    app, client = app_client

    app.dependency_overrides[admin_recommendations.get_tour_package_service] = lambda: mock_service
    app.dependency_overrides[admin_recommendations.check_admin_role] = lambda: admin_user

    mock_service.set_admin_setting.return_value = False

    payload = {"enabled": True}
    resp = client.put("/api/v1/tour-packages/admin/recommendations", json=payload)
    assert resp.status_code == 500
    assert "Failed to save admin recommendation setting" in resp.text


