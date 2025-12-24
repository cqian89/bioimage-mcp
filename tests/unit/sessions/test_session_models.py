import pytest
from pydantic import ValidationError

from bioimage_mcp.sessions import Session, SessionExport, SessionStep


def test_session_minimal():
    session = Session(session_id="session-123", status="active")
    assert session.session_id == "session-123"
    assert session.status == "active"
    assert isinstance(session.created_at, str)
    assert isinstance(session.last_activity_at, str)


def test_session_step_minimal():
    step = SessionStep(
        session_id="session-123",
        step_id="step-456",
        ordinal=1,
        fn_id="cellpose.segment",
        inputs={"image": "ref-1"},
        params={"diameter": 30},
        status="running",
    )
    assert step.session_id == "session-123"
    assert step.step_id == "step-456"
    assert step.ordinal == 1
    assert step.fn_id == "cellpose.segment"
    assert step.status == "running"
    assert step.canonical is True


def test_session_invalid_status():
    with pytest.raises(ValidationError):
        Session(session_id="s1", status="invalid-status")


def test_session_step_invalid_status():
    with pytest.raises(ValidationError):
        SessionStep(
            session_id="s1",
            step_id="st1",
            ordinal=1,
            fn_id="f1",
            inputs={},
            params={},
            status="invalid-status",
        )


def test_session_export_minimal():
    export = SessionExport(session_id="session-123", steps=[])
    assert export.session_id == "session-123"
    assert export.steps == []
    assert export.schema_version == "0.1"
