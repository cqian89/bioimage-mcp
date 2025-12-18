from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.store import ArtifactStore


class ArtifactsService:
    def __init__(self, store: ArtifactStore):
        self._store = store

    def get_artifact(self, ref_id: str) -> dict:
        return self._store.get_payload(ref_id)

    def export_artifact(self, ref_id: str, dest_path: str) -> dict:
        exported = self._store.export(ref_id, dest_path=Path(dest_path))
        return {"exported_path": str(exported)}
