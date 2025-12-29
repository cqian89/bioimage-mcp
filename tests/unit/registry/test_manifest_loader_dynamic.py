from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import load_manifest_file


def test_load_manifest_parses_dynamic_sources(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text(
        """
manifest_version: "1.0"
tool_id: tools.dynamic
tool_version: "0.1.0"
name: Dynamic Tools
description: Tools discovered dynamically
env_id: bioimage-mcp-base
entrypoint: bioimage_mcp_dynamic.entrypoint
platforms_supported: [linux-64]
functions: []
dynamic_sources:
  - adapter: skimage
    prefix: dynamic
    modules:
      - bioimage_mcp_dynamic.ops
    include_patterns: ["segment_*", "filter_*"]
    exclude_patterns: ["test_*", "_*"]
""".lstrip()
    )

    manifest, diagnostic = load_manifest_file(path)

    assert diagnostic is None
    assert manifest is not None
    assert len(manifest.dynamic_sources) == 1

    source = manifest.dynamic_sources[0]
    assert source.adapter == "skimage"
    assert source.prefix == "dynamic"
    assert source.modules == ["bioimage_mcp_dynamic.ops"]
    assert source.include_patterns == ["segment_*", "filter_*"]
    assert source.exclude_patterns == ["test_*", "_*"]
