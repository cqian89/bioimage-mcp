from datetime import UTC, datetime, timedelta

import pytest

import bioimage_mcp.sessions.store as session_store
from bioimage_mcp.sessions.models import Session, SessionStep


class TestSessionStoreCRUD:
    def test_create_and_get_session(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_123"
        hint = "mcp-client-1"

        session = store.create_session(session_id, connection_hint=hint)

        assert isinstance(session, Session)
        assert session.session_id == session_id
        assert session.connection_hint == hint
        assert session.status == "active"

        retrieved = store.get_session(session_id)
        assert retrieved.session_id == session_id
        assert retrieved.connection_hint == hint

    def test_get_missing_session_raises(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        with pytest.raises(KeyError):
            store.get_session("ghost_session")

    def test_update_activity_overrides_timestamp(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_activity_explicit"
        store.create_session(session_id)

        future_time = datetime.now(UTC) + timedelta(minutes=5)
        updated = store.update_activity(session_id, last_activity_at=future_time)

        assert updated.last_activity_at == future_time.isoformat()

    def test_update_activity_defaults_to_now(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_activity_default"
        store.create_session(session_id)

        before = datetime.now(UTC)
        updated = store.update_activity(session_id)
        after = datetime.now(UTC)

        last_activity = datetime.fromisoformat(updated.last_activity_at)
        assert before <= last_activity <= after + timedelta(seconds=1)

    def test_add_and_list_step_attempts(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_steps"
        store.create_session(session_id)

        started_at = datetime.now(UTC)
        ended_at = started_at + timedelta(seconds=5)
        step = store.add_step_attempt(
            session_id=session_id,
            step_id="step_1",
            ordinal=0,
            fn_id="base.gaussian",
            inputs={"image": "artifact_1"},
            params={"sigma": 1.5},
            status="running",
            started_at=started_at,
            ended_at=ended_at,
            run_id="run_1",
            outputs={"image": "artifact_2"},
            error=None,
            log_ref_id="log_1",
            canonical=False,
        )

        assert isinstance(step, SessionStep)
        assert step.session_id == session_id
        assert step.step_id == "step_1"
        assert step.ordinal == 0
        assert step.fn_id == "base.gaussian"
        assert step.status == "running"
        assert step.started_at == started_at.isoformat()
        assert step.ended_at == ended_at.isoformat()
        assert step.run_id == "run_1"
        assert step.outputs == {"image": "artifact_2"}
        assert step.error is None
        assert step.log_ref_id == "log_1"
        assert step.canonical is False

        attempts = store.list_step_attempts(session_id)
        assert len(attempts) == 1
        assert attempts[0].step_id == "step_1"

    def test_add_step_attempt_missing_session_raises(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        with pytest.raises(KeyError):
            store.add_step_attempt(
                session_id="missing_session",
                step_id="step_1",
                ordinal=0,
                fn_id="base.gaussian",
                inputs={},
                params={},
                status="running",
                started_at=datetime.now(UTC),
            )

    def test_list_step_attempts_missing_session_raises(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        with pytest.raises(KeyError):
            store.list_step_attempts("missing_session")

    def test_set_canonical_sets_single_attempt(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_canon"
        store.create_session(session_id)

        store.add_step_attempt(
            session_id=session_id,
            step_id="step_1",
            ordinal=0,
            fn_id="base.gaussian",
            inputs={},
            params={},
            status="succeeded",
            started_at=datetime.now(UTC),
            canonical=True,
        )
        store.add_step_attempt(
            session_id=session_id,
            step_id="step_1_retry",
            ordinal=0,
            fn_id="base.gaussian",
            inputs={},
            params={},
            status="succeeded",
            started_at=datetime.now(UTC),
            canonical=False,
        )

        store.set_canonical(session_id, "step_1_retry", ordinal=0)

        attempts = store.list_step_attempts(session_id)
        canon = next(a for a in attempts if a.step_id == "step_1_retry")
        other = next(a for a in attempts if a.step_id == "step_1")

        assert canon.canonical is True
        assert other.canonical is False

    def test_set_canonical_missing_session_raises(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        with pytest.raises(KeyError):
            store.set_canonical("missing_session", "step_1", ordinal=0)

    def test_active_functions_replace_and_get(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_fns"
        store.create_session(session_id)

        assert store.get_active_functions(session_id) == []

        first = ["base.gaussian", "base.median"]
        replaced = store.replace_active_functions(session_id, first)
        assert replaced == first
        assert store.get_active_functions(session_id) == first

        later = ["cellpose.segment"]
        store.replace_active_functions(session_id, later)
        assert store.get_active_functions(session_id) == later

    def test_active_functions_missing_session_raises(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        with pytest.raises(KeyError):
            store.get_active_functions("missing_session")
        with pytest.raises(KeyError):
            store.replace_active_functions("missing_session", ["fn_1"])

    def test_update_session_status(self):
        store_cls = getattr(session_store, "SessionStore", None)
        assert store_cls is not None, "SessionStore class is missing in bioimage_mcp.sessions.store"
        store = store_cls()

        session_id = "sess_status_update"
        store.create_session(session_id)

        store.update_session_status(session_id, "exported")
        session = store.get_session(session_id)
        assert session.status == "exported"

        with pytest.raises(KeyError):
            store.update_session_status("missing_session", "exported")
