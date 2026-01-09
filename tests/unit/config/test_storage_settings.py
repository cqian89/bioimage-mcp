import pytest
from pydantic import ValidationError
from bioimage_mcp.config.schema import Config, StorageSettings


def test_storage_settings_defaults():
    settings = StorageSettings()
    assert settings.quota_bytes == 53687091200
    assert settings.warning_threshold == 0.80
    assert settings.critical_threshold == 0.95
    assert settings.retention_days == 7
    assert settings.auto_cleanup_enabled is False


def test_storage_settings_validation_thresholds():
    # Valid thresholds
    StorageSettings(warning_threshold=0.7, critical_threshold=0.8)

    # Invalid: critical <= warning
    with pytest.raises(
        ValidationError, match="critical_threshold must be greater than warning_threshold"
    ):
        StorageSettings(warning_threshold=0.9, critical_threshold=0.8)

    with pytest.raises(
        ValidationError, match="critical_threshold must be greater than warning_threshold"
    ):
        StorageSettings(warning_threshold=0.9, critical_threshold=0.9)


def test_config_includes_storage_settings(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    assert hasattr(config, "storage")
    assert isinstance(config.storage, StorageSettings)
