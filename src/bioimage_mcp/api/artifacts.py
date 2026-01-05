from __future__ import annotations

from bioimage_mcp.artifacts.store import ArtifactStore


class ArtifactsService:
    def __init__(self, store: ArtifactStore):
        self._store = store

    def get_artifact(self, ref_id: str) -> dict:
        return self._store.get_payload(ref_id)
