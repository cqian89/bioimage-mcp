from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


def _load_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "scripts" / "ci" / "prepare_ci_config.py"
    spec = importlib.util.spec_from_file_location("prepare_ci_config", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_ci_config_rewrites_local_config(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    config_dir = repo_root / ".bioimage-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "artifact_store_root": "/tmp/original-artifacts",
                "tool_manifest_roots": ["/tmp/original-tools"],
                "fs_allowlist_read": [],
                "fs_allowlist_write": ["/tmp/original-write"],
                "fs_denylist": ["/etc", "/proc"],
                "microsam": {"device": "auto"},
            },
            sort_keys=False,
        )
    )

    module = _load_module()

    result_path = module.prepare_ci_config(repo_root)

    assert result_path == config_path

    rewritten = yaml.safe_load(config_path.read_text())
    expected_artifact_root = repo_root / ".tmp" / "ci" / "artifacts"

    assert rewritten["artifact_store_root"] == str(expected_artifact_root)
    assert rewritten["fs_allowlist_read"] == [str(repo_root / "datasets"), str(repo_root)]
    assert rewritten["fs_allowlist_write"] == [
        str(repo_root / ".tmp"),
        str(repo_root / "datasets" / "synthetic"),
        str(repo_root),
        str(expected_artifact_root),
    ]
    assert rewritten["tool_manifest_roots"] == ["/tmp/original-tools"]
    assert rewritten["fs_denylist"] == ["/etc", "/proc"]
    assert rewritten["microsam"] == {"device": "auto"}


def test_prepare_ci_config_main_uses_current_working_directory(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    config_dir = repo_root / ".bioimage-mcp"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("artifact_store_root: /tmp/old\n")

    module = _load_module()

    monkeypatch.chdir(repo_root)

    exit_code = module.main([])

    assert exit_code == 0

    rewritten = yaml.safe_load((config_dir / "config.yaml").read_text())
    assert rewritten["artifact_store_root"] == str(repo_root / ".tmp" / "ci" / "artifacts")
