from pathlib import Path
from bioimage_mcp.config.schema import PermissionSettings, PermissionMode, Config


def test_permission_settings_default_is_hybrid():
    """Default permission mode should be HYBRID for better out-of-box experience."""
    settings = PermissionSettings()
    assert settings.mode == PermissionMode.HYBRID


def test_config_uses_hybrid_permissions_by_default():
    """Config should use HYBRID permission settings by default."""
    config = Config(
        artifact_store_root=Path("/tmp/artifacts"),
        tool_manifest_roots=[Path("/tmp/tools")],
    )
    assert config.permissions.mode == PermissionMode.HYBRID
