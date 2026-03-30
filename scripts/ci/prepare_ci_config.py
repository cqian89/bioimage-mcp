from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def prepare_ci_config(repo_root: Path) -> Path:
    """Rewrite the local config for CI smoke runs from the repo root."""
    repo_root = repo_root.resolve()
    config_path = repo_root / ".bioimage-mcp" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    data = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    artifact_store_root = repo_root / ".tmp" / "ci" / "artifacts"
    allowlist_read = [
        repo_root / "datasets",
        repo_root,
    ]
    allowlist_write = [
        repo_root / ".tmp",
        repo_root / "datasets" / "synthetic",
        repo_root,
        artifact_store_root,
    ]

    artifact_store_root.mkdir(parents=True, exist_ok=True)
    for path in allowlist_write[:-1]:
        path.mkdir(parents=True, exist_ok=True)

    data["artifact_store_root"] = str(artifact_store_root)
    data["fs_allowlist_read"] = [str(path) for path in allowlist_read]
    data["fs_allowlist_write"] = [str(path) for path in allowlist_write]

    config_path.write_text(yaml.safe_dump(data, sort_keys=False))
    return config_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rewrite local Bioimage-MCP config for CI.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root containing .bioimage-mcp/config.yaml",
    )
    args = parser.parse_args(argv)

    config_path = prepare_ci_config(Path(args.repo_root))
    print(f"Prepared CI config: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
