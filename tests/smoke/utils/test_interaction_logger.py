import json
from pathlib import Path
import pytest
from datetime import datetime, timezone

# These imports will fail until the implementation is created in the next task
# This is expected for the TDD red phase.
from tests.smoke.utils.interaction_logger import (
    Interaction,
    InteractionLog,
    InteractionLogger,
)


def test_interaction_model_request_validation():
    """Test Interaction model for request direction"""
    interaction = Interaction(
        timestamp=datetime.now(timezone.utc).isoformat(),
        direction="request",
        tool="run",
        params={"fn_id": "base.gaussian_blur", "inputs": {}},
        correlation_id="test-id",
    )
    assert interaction.direction == "request"
    assert interaction.tool == "run"
    assert interaction.params["fn_id"] == "base.gaussian_blur"


def test_interaction_model_response_validation():
    """Test Interaction model for response direction"""
    interaction = Interaction(
        timestamp=datetime.now(timezone.utc).isoformat(),
        direction="response",
        tool="run",
        result={"artifact_id": "art-123"},
        duration_ms=150.5,
        correlation_id="test-id",
    )
    assert interaction.direction == "response"
    assert interaction.result["artifact_id"] == "art-123"
    assert interaction.duration_ms == 150.5


def test_interaction_log_model_creation():
    """Test InteractionLog model with required fields"""
    now = datetime.now(timezone.utc).isoformat()
    log = InteractionLog(
        test_run_id="smoke_2026-01-08_143022",
        scenario="flim_phasor",
        started_at=now,
    )
    assert log.test_run_id == "smoke_2026-01-08_143022"
    assert log.scenario == "flim_phasor"
    assert log.started_at == now


def test_interaction_log_model_defaults():
    """Test default values (status="running", interactions=[])"""
    log = InteractionLog(
        test_run_id="test",
        scenario="test",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    assert log.status == "running"
    assert log.interactions == []
    assert log.server_stderr is None


def test_interaction_logger_log_request():
    """Test logging a request returns correlation_id"""
    logger = InteractionLogger(test_run_id="test", scenario="test")
    params = {"x": 1}
    correlation_id = logger.log_request("run", params)
    assert isinstance(correlation_id, str)
    assert len(logger.log.interactions) == 1
    assert logger.log.interactions[0].direction == "request"
    assert logger.log.interactions[0].params == params
    assert logger.log.interactions[0].correlation_id == correlation_id


def test_interaction_logger_log_response():
    """Test logging a response with correlation_id"""
    logger = InteractionLogger(test_run_id="test", scenario="test")
    correlation_id = logger.log_request("run", {"x": 1})
    result = {"status": "ok"}
    logger.log_response(correlation_id, result, duration_ms=100.0)

    # log_request adds 1, log_response adds 1
    assert len(logger.log.interactions) == 2
    response = logger.log.interactions[1]
    assert response.direction == "response"
    assert response.result == result
    assert response.correlation_id == correlation_id
    assert response.duration_ms == 100.0


def test_interaction_logger_truncate_small_payload():
    """Test that small payloads pass through unchanged"""
    logger = InteractionLogger(test_run_id="test", scenario="test")
    small_data = {"key": "value"}
    truncated = logger._truncate(small_data)
    assert truncated == small_data


def test_interaction_logger_truncate_large_payload():
    """Test that large payloads (>10KB) get truncated"""
    logger = InteractionLogger(test_run_id="test", scenario="test")
    # Create data larger than 10KB (10 * 1024 = 10240 bytes)
    large_data = {"large_string": "x" * 11000}
    truncated = logger._truncate(large_data)
    assert truncated["_truncated"] is True
    assert "_size" in truncated
    assert "large_string" not in truncated


def test_interaction_logger_save(tmp_path):
    """Test saving log to file"""
    log_path = tmp_path / "interaction_log.json"
    logger = InteractionLogger(test_run_id="test_run", scenario="test_scenario")
    logger.log_request("list", {})
    logger.save(log_path)

    assert log_path.exists()
    with open(log_path) as f:
        data = json.load(f)
    assert data["test_run_id"] == "test_run"
    assert data["scenario"] == "test_scenario"
    assert len(data["interactions"]) == 1
