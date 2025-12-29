from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.permissions import PermissionService
from bioimage_mcp.artifacts.store import ArtifactStore


class ArtifactsService:
    def __init__(
        self, store: ArtifactStore, *, permission_service: PermissionService | None = None
    ):
        self._store = store
        self._permission_service = permission_service

    def get_artifact(self, ref_id: str) -> dict:
        return self._store.get_payload(ref_id)

    def export_artifact(
        self,
        ref_id: str,
        dest_path: str,
        *,
        session: object | None = None,
        permission_service: PermissionService | None = None,
    ) -> dict:
        exported = self._store.export(
            ref_id,
            dest_path=Path(dest_path),
            session=session,
            permission_service=permission_service or self._permission_service,
        )
        return {"exported_path": str(exported)}
