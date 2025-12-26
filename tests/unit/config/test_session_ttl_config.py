import pytest
from pydantic import ValidationError

from bioimage_mcp.config.loader import load_config
from bioimage_mcp.config.schema import Config


def test_config_has_session_ttl_field():
    """Verify Config model has session_ttl_hours field with default 24."""
    # Minimal valid config
    config = Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=[],
    )
    assert hasattr(config, "session_ttl_hours")
    assert config.session_ttl_hours == 24


def test_config_override_session_ttl():
    """Verify session_ttl_hours can be overridden during instantiation."""
    config = Config(
        artifact_store_root="/tmp/artifacts", tool_manifest_roots=[], session_ttl_hours=48
    )
    assert config.session_ttl_hours == 48


def test_config_validation_session_ttl_positive():
    """Verify session_ttl_hours must be > 0."""
    # 0 should fail
    with pytest.raises(ValidationError) as excinfo:
        Config(artifact_store_root="/tmp/artifacts", tool_manifest_roots=[], session_ttl_hours=0)
    assert "session_ttl_hours" in str(excinfo.value)

    # Negative should fail
    with pytest.raises(ValidationError):
        Config(artifact_store_root="/tmp/artifacts", tool_manifest_roots=[], session_ttl_hours=-1)


def test_load_config_defaults_ttl(tmp_path):
    """Verify load_config uses default TTL when not specified in yaml."""
    global_config = tmp_path / "global_config.yaml"
    local_config = tmp_path / "local_config.yaml"

    # Empty files (valid yaml)
    global_config.write_text("")
    local_config.write_text("")

    config = load_config(global_path=global_config, local_path=local_config)
    assert config.session_ttl_hours == 24


def test_load_config_overrides_ttl(tmp_path):
    """Verify load_config picks up session_ttl_hours from yaml."""
    global_config = tmp_path / "global_config.yaml"
    local_config = tmp_path / "local_config.yaml"

    global_config.write_text("session_ttl_hours: 72")
    local_config.write_text("")

    config = load_config(global_path=global_config, local_path=local_config)
    assert config.session_ttl_hours == 72

    # Local overrides global
    local_config.write_text("session_ttl_hours: 12")
    config = load_config(global_path=global_config, local_path=local_config)
    assert config.session_ttl_hours == 12
