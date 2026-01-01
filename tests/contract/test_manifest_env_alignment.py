from pathlib import Path

import yaml


def test_manifest_python_version_matches_env():
    """Verify manifest python_version aligns with env files."""
    repo_root = Path(__file__).parents[2]
    tools_dir = repo_root / "tools"
    envs_dir = repo_root / "envs"

    manifest_files = list(tools_dir.glob("*/manifest.yaml"))
    assert len(manifest_files) > 0, "No manifest files found in tools/"

    for manifest_path in manifest_files:
        manifest = yaml.safe_load(manifest_path.read_text())
        env_id = manifest.get("env_id")
        manifest_py = manifest.get("python_version")

        if not env_id or not manifest_py:
            continue

        env_file = envs_dir / f"{env_id}.yaml"
        if not env_file.exists():
            # Skip if no matching env file (some may use lockfiles only as per instructions)
            continue

        env_data = yaml.safe_load(env_file.read_text())
        deps = env_data.get("dependencies", [])

        found_python = False
        # Find python=X.Y in dependencies
        for dep in deps:
            if isinstance(dep, str) and dep.startswith("python="):
                # Handle python=3.11 or python=3.11,<3.12
                env_py = dep.split("=")[1].split(",")[0]
                assert manifest_py == env_py, (
                    f"Manifest {manifest_path} python_version={manifest_py} "
                    f"doesn't match env {env_file.name} python={env_py}"
                )
                found_python = True
                break

        assert found_python, f"No python dependency found in {env_file}"
