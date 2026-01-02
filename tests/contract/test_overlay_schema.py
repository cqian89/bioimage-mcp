import yaml

from bioimage_mcp.registry.manifest_schema import ToolManifest


def test_manifest_with_overlays_schema(tmp_path):
    """Verify that ToolManifest can load and validate function_overlays."""
    manifest_yaml = """
manifest_version: "0.0"
tool_id: tools.test
tool_version: "0.1.0"
env_id: bioimage-mcp-test
entrypoint: main.py
dynamic_sources:
  - adapter: skimage
    prefix: skimage
    modules: ["skimage.filters"]
function_overlays:
  "tools.test.skimage.filters.gaussian":
    description: "Overridden description"
    tags: ["enhanced", "blur"]
    params_override:
      sigma:
        description: "Standard deviation"
        default: 1.0
"""
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(manifest_yaml)

    # This should fail currently because ToolManifest doesn't have function_overlays field
    # and pydantic (default config) might either ignore extra fields or fail if extra="forbid"
    # ToolManifest doesn't seem to have extra="forbid", but we want to assert it HAS the field.

    manifest_data = yaml.safe_load(manifest_yaml)
    manifest_data["manifest_path"] = manifest_path
    manifest_data["manifest_checksum"] = "dummy"

    manifest = ToolManifest.model_validate(manifest_data)

    # If it's not in the model, this attribute access will fail
    assert hasattr(manifest, "function_overlays"), (
        "ToolManifest should have 'function_overlays' field"
    )
    assert "tools.test.skimage.filters.gaussian" in manifest.function_overlays
    overlay = manifest.function_overlays["tools.test.skimage.filters.gaussian"]
    assert overlay.description == "Overridden description"
