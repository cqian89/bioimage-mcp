from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvManager:
    name: str
    executable: str
    version: str | None


def _get_version(executable: str) -> str | None:
    try:
        proc = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:  # noqa: BLE001
        return None

    out = (proc.stdout or proc.stderr).strip()
    return out.splitlines()[0] if out else None


def get_available_envs() -> list[str]:
    """List available conda/mamba/micromamba environments."""
    detected = detect_env_manager()
    if not detected:
        return []

    name, exe, _ = detected
    try:
        # Both conda/mamba/micromamba support 'env list'
        proc = subprocess.run(
            [exe, "env", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode != 0:
            return []

        envs = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format is usually 'name   path' or just 'path' for anonymous envs
            parts = line.split()
            if parts:
                envs.append(parts[0])
        return envs
    except Exception:  # noqa: BLE001
        return []


def detect_env_manager() -> tuple[str, str, str | None] | None:
    """Detect an available conda-like env manager.

    Preference order: micromamba, mamba, conda.
    """

    for name in ("micromamba", "mamba", "conda"):
        path = shutil.which(name)
        if path:
            return (name, path, _get_version(path))

    return None


_ENV_PATH_CACHE: dict[str, Path] | None = None


def get_env_paths() -> dict[str, Path]:
    """Return mapping of conda env name -> env path."""
    global _ENV_PATH_CACHE
    if _ENV_PATH_CACHE is not None:
        return dict(_ENV_PATH_CACHE)

    detected = detect_env_manager()
    if not detected:
        _ENV_PATH_CACHE = {}
        return {}

    _name, exe, _version = detected
    try:
        proc = subprocess.run(
            [exe, "env", "list", "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if proc.returncode != 0:
            _ENV_PATH_CACHE = {}
            return {}

        data = json.loads(proc.stdout or "{}")
        envs: dict[str, Path] = {}
        for env_path in data.get("envs", []) or []:
            if not isinstance(env_path, str):
                continue
            name = env_path.replace("\\", "/").split("/")[-1]
            envs[name] = Path(env_path)
        _ENV_PATH_CACHE = envs
        return dict(_ENV_PATH_CACHE)
    except Exception:  # noqa: BLE001
        _ENV_PATH_CACHE = {}
        return {}
