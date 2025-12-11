"""
Unit tests for AdminSettingsService
"""
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from app.v1.services.admin_settings_service import AdminSettingsService


@pytest.fixture
def mock_supabase():
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    return mock_client, mock_table


def test_get_admin_setting_returns_value(mock_supabase):
    client, table = mock_supabase
    table.select().eq().execute.return_value = Mock(data=[{"setting_value": True}])

    service = AdminSettingsService(client)
    value = service.get_admin_setting("ADMIN_RECOMMENDATION_ENABLED", default_value=False)

    assert value is True
    table.select.assert_called_once()


def test_get_admin_setting_returns_default_when_missing(mock_supabase):
    client, table = mock_supabase
    table.select().eq().execute.return_value = Mock(data=[])

    service = AdminSettingsService(client)
    value = service.get_admin_setting("ADMIN_RECOMMENDATION_ENABLED", default_value=False)

    assert value is False


def test_set_admin_setting_sets_admin_id(mock_supabase):
    client, table = mock_supabase
    table.upsert.return_value = Mock(data=[{"setting_key": "ADMIN_RECOMMENDATION_ENABLED"}])

    service = AdminSettingsService(client)
    now_before = datetime.now(timezone.utc)
    ok = service.set_admin_setting("ADMIN_RECOMMENDATION_ENABLED", True, updated_by="admin-123")
    now_after = datetime.now(timezone.utc)

    assert ok is True
    assert table.upsert.call_count == 1
    args, kwargs = table.upsert.call_args
    payload = args[0]
    assert payload["setting_key"] == "ADMIN_RECOMMENDATION_ENABLED"
    assert payload["setting_value"] is True
    assert payload["admin_id"] == "admin-123"
    # updated_at exists and is within reasonable range
    assert "updated_at" in payload
    ts = datetime.fromisoformat(payload["updated_at"])
    assert now_before <= ts <= now_after


