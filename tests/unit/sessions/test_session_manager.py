from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.models import Session
from bioimage_mcp.sessions.store import SessionStore


class TestSessionManager:
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.session_ttl_hours = 24
        return config

    def test_init(self, mock_config):
        """Test initialization stores the store reference."""
        store = SessionStore()
        manager = SessionManager(store, mock_config)
        assert manager.store is store
        assert manager.config is mock_config

    def test_ensure_session_creates_new_if_missing(self, mock_config):
        """Test ensure_session creates a new session if it doesn't exist."""
        store = Mock(spec=SessionStore)
        # Setup: get_session raises KeyError
        store.get_session.side_effect = KeyError("Not found")
        new_session = Session(session_id="sess-1")
        store.create_session.return_value = new_session

        manager = SessionManager(store, mock_config)
        result = manager.ensure_session("sess-1", connection_hint="hint")

        # It should try to get it, fail, then create it
        store.get_session.assert_called_once_with("sess-1")
        store.create_session.assert_called_once_with("sess-1", connection_hint="hint")
        assert result == new_session

    def test_ensure_session_returns_existing_and_updates_activity(self, mock_config):
        """Test ensure_session returns existing session and updates its activity."""
        store = Mock(spec=SessionStore)
        # Setup: get_session returns existing session
        existing_session = Session(
            session_id="sess-1", last_activity_at=datetime.now(UTC).isoformat()
        )
        store.get_session.return_value = existing_session

        updated_session = Session(session_id="sess-1", last_activity_at="2024-01-01T12:00:00")
        store.update_activity.return_value = updated_session

        manager = SessionManager(store, mock_config)
        result = manager.ensure_session("sess-1")

        store.get_session.assert_called_with("sess-1")
        store.update_activity.assert_called_once_with("sess-1")
        assert result == updated_session

    def test_update_activity(self, mock_config):
        """Test update_activity delegates to store."""
        store = Mock(spec=SessionStore)
        manager = SessionManager(store, mock_config)

        manager.update_activity("sess-1")

        store.update_activity.assert_called_once_with("sess-1")

    def test_get_session_success(self, mock_config):
        """Test get_session returns session from store."""
        store = Mock(spec=SessionStore)
        expected_session = Session(
            session_id="sess-1", last_activity_at=datetime.now(UTC).isoformat()
        )
        store.get_session.return_value = expected_session

        manager = SessionManager(store, mock_config)
        result = manager.get_session("sess-1")

        store.get_session.assert_called_once_with("sess-1")
        assert result == expected_session

    def test_get_session_missing(self, mock_config):
        """Test get_session raises KeyError if session missing."""
        store = Mock(spec=SessionStore)
        store.get_session.side_effect = KeyError("Not found")

        manager = SessionManager(store, mock_config)
        with pytest.raises(KeyError):
            manager.get_session("missing")

    def test_get_session_expired(self, mock_config):
        """Test get_session raises ValueError and updates status if expired."""
        store = Mock(spec=SessionStore)
        # Create an expired session
        # TTL is 24 hours. Make it 25 hours old.
        old_time = datetime.now(UTC) - timedelta(hours=25)
        expired_session = Session(
            session_id="sess-expired", last_activity_at=old_time.isoformat(), status="active"
        )
        store.get_session.return_value = expired_session

        manager = SessionManager(store, mock_config)

        with pytest.raises(ValueError, match="is expired"):
            manager.get_session("sess-expired")

        store.update_session_status.assert_called_once_with("sess-expired", "expired")

    def test_ensure_session_expired(self, mock_config):
        """Test ensure_session raises ValueError if existing session is expired."""
        store = Mock(spec=SessionStore)
        old_time = datetime.now(UTC) - timedelta(hours=25)
        expired_session = Session(
            session_id="sess-expired", last_activity_at=old_time.isoformat(), status="active"
        )
        store.get_session.return_value = expired_session

        manager = SessionManager(store, mock_config)

        with pytest.raises(ValueError, match="is expired"):
            manager.ensure_session("sess-expired")

        store.update_session_status.assert_called_once_with("sess-expired", "expired")
        # Should NOT update activity
        store.update_activity.assert_not_called()

    def test_check_expiry_already_expired_status(self, mock_config):
        """Test check_expiry raises if status is already expired."""
        store = Mock(spec=SessionStore)
        expired_session = Session(
            session_id="sess-expired",
            last_activity_at=datetime.now(
                UTC
            ).isoformat(),  # time doesn't matter if status is expired
            status="expired",
        )
        store.get_session.return_value = expired_session

        manager = SessionManager(store, mock_config)

        with pytest.raises(ValueError, match="is expired"):
            manager.check_expiry("sess-expired")

        # Should not call update_session_status again if already expired (optimization)
        # But my implementation checks status first, so it raises.
        store.update_session_status.assert_not_called()

    def test_integration_with_real_store(self):
        """Integration test using real SessionStore."""
        store = SessionStore()  # In-memory
        config = Config(artifact_store_root="/tmp", tool_manifest_roots=[], session_ttl_hours=1)
        manager = SessionManager(store, config)

        # 1. Create new
        s1 = manager.ensure_session("sess-real", connection_hint="test-hint")
        assert s1.session_id == "sess-real"
        assert s1.connection_hint == "test-hint"

        # 2. Get existing
        s2 = manager.get_session("sess-real")
        assert s2.session_id == "sess-real"

        # 3. Ensure existing (updates activity)
        s3 = manager.ensure_session("sess-real")
        assert s3.session_id == "sess-real"

        # 4. Update activity explicitly
        manager.update_activity("sess-real")

    def test_complete_session_calls_callbacks(self, mock_config):
        """Test complete_session updates store and calls registered callbacks."""
        store = Mock(spec=SessionStore)
        session_id = "sess-1"
        expected_session = Session(session_id=session_id, status="completed")
        store.complete_session.return_value = expected_session

        manager = SessionManager(store, mock_config)
        callback = Mock()
        manager.register_on_session_complete(callback)

        result = manager.complete_session(session_id)

        store.complete_session.assert_called_once_with(session_id)
        callback.assert_called_once_with(session_id)
        assert result == expected_session
