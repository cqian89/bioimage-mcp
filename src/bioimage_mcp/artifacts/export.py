from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.store import ArtifactStore


def export_artifact(store: ArtifactStore, *, ref_id: str, dest_path: Path) -> Path:
    return store.export(ref_id, dest_path)
