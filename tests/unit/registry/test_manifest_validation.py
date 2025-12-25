from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import load_manifest_file


def test_load_manifest_validates_and_computes_checksum(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.builtin
tool_version: "0.0.0"
name: Built-ins
description: Built-in functions
env_id: bioimage-mcp-base
entrypoint: bioimage_mcp_builtin.entrypoint
platforms_supported: [linux-64]
functions:
  - fn_id: builtin.gaussian_blur
    tool_id: tools.builtin
    name: Gaussian blur
    description: Blur an image
    tags: [image, filter]
    inputs:
      - name: image
        artifact_type: BioImageRef
        required: true
    outputs:
      - name: output
        artifact_type: BioImageRef
        required: true
    params_schema:
      type: object
""".lstrip()
    )

    manifest, diagnostic = load_manifest_file(path)

    assert diagnostic is None
    assert manifest is not None
    assert manifest.manifest_path == path
    assert manifest.manifest_checksum


def test_load_manifest_invalid_returns_diagnostic(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text("tool_id: tools.builtin\n")

    manifest, diagnostic = load_manifest_file(path)

    assert manifest is None
    assert diagnostic is not None
    assert diagnostic.path == path
    assert diagnostic.errors


def test_manifest_rejects_bad_env_id(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.builtin
tool_version: "0.0.0"
env_id: base
entrypoint: x
platforms_supported: [linux-64]
functions: []
""".lstrip()
    )

    manifest, diagnostic = load_manifest_file(path)
    assert manifest is None
    assert diagnostic is not None

    joined = "\n".join(diagnostic.errors)
    assert "env_id" in joined


def test_manifest_rejects_duplicate_dynamic_source_prefixes(tmp_path: Path) -> None:
    """ToolManifest should reject duplicate prefixes in dynamic_sources."""
    path = tmp_path / "manifest.yaml"
    path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.test
tool_version: "0.0.0"
env_id: bioimage-mcp-test
entrypoint: test.entrypoint
platforms_supported: [linux-64]
functions: []
dynamic_sources:
  - adapter: python_api
    prefix: skimage
    modules: [skimage.filters]
  - adapter: python_api
    prefix: skimage
    modules: [skimage.transform]
""".lstrip()
    )

    manifest, diagnostic = load_manifest_file(path)
    assert manifest is None
    assert diagnostic is not None

    joined = "\n".join(diagnostic.errors)
    assert "prefix" in joined.lower()
    assert "duplicate" in joined.lower() or "unique" in joined.lower()
