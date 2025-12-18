from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


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


def detect_env_manager() -> tuple[str, str, str | None] | None:
    """Detect an available conda-like env manager.

    Preference order: micromamba, mamba, conda.
    """

    for name in ("micromamba", "mamba", "conda"):
        path = shutil.which(name)
        if path:
            return (name, path, _get_version(path))

    return None
