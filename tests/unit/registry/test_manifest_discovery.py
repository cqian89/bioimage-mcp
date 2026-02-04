from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import discover_manifest_paths


def test_discover_manifest_paths_ignores_non_manifest_yamls(tmp_path: Path) -> None:
    # Create a temp directory with multiple YAML files
    tools_root = tmp_path / "tools"
    tools_root.mkdir()

    foo_dir = tools_root / "foo"
    foo_dir.mkdir()
    (foo_dir / "manifest.yaml").write_text("tool_id: foo")
    (foo_dir / "not_a_manifest.yaml").write_text("not: a manifest")

    bar_dir = tools_root / "bar"
    bar_dir.mkdir()
    (bar_dir / "manifest.yml").write_text("tool_id: bar")
    (bar_dir / "other.yml").write_text("some: other content")

    # Call discover_manifest_paths
    paths = discover_manifest_paths([tools_root])

    # Assert it returns ONLY the manifest files
    expected = {
        (foo_dir / "manifest.yaml").resolve(),
        (bar_dir / "manifest.yml").resolve(),
    }
    actual = {p.resolve() for p in paths}

    assert actual == expected
    assert len(paths) == 2
