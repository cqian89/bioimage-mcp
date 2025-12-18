from __future__ import annotations

from pathlib import Path


def configure() -> int:
    """Write a starter local configuration file."""

    config_dir = Path.cwd() / ".bioimage-mcp"
    config_dir.mkdir(parents=True, exist_ok=True)

    path = config_dir / "config.yaml"
    if path.exists():
        print(f"Config already exists: {path}")
        return 0

    home = Path.home()
    content = """
artifact_store_root: {artifact_store_root}
tool_manifest_roots:
  - {tool_manifest_root}
fs_allowlist_read: []
fs_allowlist_write:
  - {write_root}
fs_denylist:
  - /etc
  - /proc
""".lstrip().format(
        artifact_store_root=str(home / ".bioimage-mcp" / "artifacts"),
        tool_manifest_root=str(home / ".bioimage-mcp" / "tools"),
        write_root=str(home / ".bioimage-mcp"),
    )

    path.write_text(content)
    print(f"Wrote {path}")
    return 0
