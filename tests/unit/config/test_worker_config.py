import pytest
from pydantic import ValidationError

from bioimage_mcp.config.loader import load_config
from bioimage_mcp.config.schema import Config


def test_config_has_worker_timeout_field():
    """Verify Config model has worker_timeout_seconds field with default 600."""
    # Minimal valid config
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
    )
    assert hasattr(config, "worker_timeout_seconds")
    assert config.worker_timeout_seconds == 600


def test_config_has_max_workers_field():
    """Verify Config model has max_workers field with default 8."""
    # Minimal valid config
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
    )
    assert hasattr(config, "max_workers")
    assert config.max_workers == 8


def test_config_has_session_timeout_field():
    """Verify Config model has session_timeout_seconds field with default 1800."""
    # Minimal valid config
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
    )
    assert hasattr(config, "session_timeout_seconds")
    assert config.session_timeout_seconds == 1800


def test_config_override_worker_timeout():
    """Verify worker_timeout_seconds can be overridden during instantiation."""
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
        worker_timeout_seconds=1200,
    )
    assert config.worker_timeout_seconds == 1200


def test_config_override_max_workers():
    """Verify max_workers can be overridden during instantiation."""
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
        max_workers=16,
    )
    assert config.max_workers == 16


def test_config_override_session_timeout():
    """Verify session_timeout_seconds can be overridden during instantiation."""
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
        session_timeout_seconds=3600,
    )
    assert config.session_timeout_seconds == 3600


def test_config_validation_worker_timeout_positive():
    """Verify worker_timeout_seconds must be > 0."""
    # 0 should fail
    with pytest.raises(ValidationError) as excinfo:
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            worker_timeout_seconds=0,
        )
    assert "worker_timeout_seconds" in str(excinfo.value)

    # Negative should fail
    with pytest.raises(ValidationError):
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            worker_timeout_seconds=-1,
        )


def test_config_validation_max_workers_positive():
    """Verify max_workers must be > 0."""
    # 0 should fail
    with pytest.raises(ValidationError) as excinfo:
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            max_workers=0,
        )
    assert "max_workers" in str(excinfo.value)

    # Negative should fail
    with pytest.raises(ValidationError):
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            max_workers=-1,
        )


def test_config_validation_session_timeout_positive():
    """Verify session_timeout_seconds must be > 0."""
    # 0 should fail
    with pytest.raises(ValidationError) as excinfo:
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            session_timeout_seconds=0,
        )
    assert "session_timeout_seconds" in str(excinfo.value)

    # Negative should fail
    with pytest.raises(ValidationError):
        Config(
            artifact_store_root="/tmp/artifacts",
            tool_manifest_roots=[],
            session_timeout_seconds=-1,
        )


def test_load_config_defaults_worker_settings(tmp_path):
    """Verify load_config uses default worker settings when not specified in yaml."""
    global_config = tmp_path / "global_config.yaml"
    local_config = tmp_path / "local_config.yaml"

    # Empty files (valid yaml)
    global_config.write_text("")
    local_config.write_text("")

    config = load_config(global_path=global_config, local_path=local_config)
    assert config.worker_timeout_seconds == 600
    assert config.max_workers == 8
    assert config.session_timeout_seconds == 1800


def test_load_config_overrides_worker_settings(tmp_path):
    """Verify load_config picks up worker settings from yaml."""
    global_config = tmp_path / "global_config.yaml"
    local_config = tmp_path / "local_config.yaml"

    global_config.write_text(
        """
worker_timeout_seconds: 1200
max_workers: 16
session_timeout_seconds: 3600
"""
    )
    local_config.write_text("")

    config = load_config(global_path=global_config, local_path=local_config)
    assert config.worker_timeout_seconds == 1200
    assert config.max_workers == 16
    assert config.session_timeout_seconds == 3600

    # Local overrides global
    local_config.write_text(
        """
worker_timeout_seconds: 300
max_workers: 4
session_timeout_seconds: 900
"""
    )
    config = load_config(global_path=global_config, local_path=local_config)
    assert config.worker_timeout_seconds == 300
    assert config.max_workers == 4
    assert config.session_timeout_seconds == 900
