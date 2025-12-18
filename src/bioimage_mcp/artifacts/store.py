from __future__ import annotations

import errno
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from bioimage_mcp.artifacts.checksums import sha256_file, sha256_tree
from bioimage_mcp.artifacts.metadata import extract_image_metadata
from bioimage_mcp.artifacts.models import ArtifactChecksum, ArtifactRef
from bioimage_mcp.config.fs_policy import assert_path_allowed
from bioimage_mcp.config.schema import Config
from bioimage_mcp.errors import ArtifactStoreError
from bioimage_mcp.storage.sqlite import connect


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _guess_mime_type(artifact_type: str, fmt: str) -> str:
    if artifact_type == "LogRef":
        return "text/plain"
    if fmt.lower() in {"ome-zarr", "zarr"}:
        return "application/zarr+ome"
    if fmt.lower() in {"ome-tiff", "tiff", "tif"}:
        return "image/tiff"
    return "application/octet-stream"


class ArtifactStore:
    def __init__(self, config: Config, *, conn: sqlite3.Connection | None = None):
        self._config = config
        self._conn = conn or connect(config)

    def _objects_dir(self) -> Path:
        return self._config.artifact_store_root / "objects"

    def _artifact_path(self, ref_id: str) -> Path:
        return self._objects_dir() / ref_id

    def import_file(self, src: Path, *, artifact_type: str, format: str) -> ArtifactRef:
        src = src.expanduser().absolute()
        if not _is_within(src, self._config.artifact_store_root):
            assert_path_allowed("read", src, self._config)

        ref_id = uuid.uuid4().hex
        dest = self._artifact_path(ref_id)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dest)
        except OSError as exc:
            if exc.errno != errno.ENOSPC:
                raise

            log_ref_id = None
            try:
                log_ref_id = self.write_log(
                    f"Disk full while importing artifact from {src} to {dest}: {exc}"
                ).ref_id
            except Exception:  # noqa: BLE001
                log_ref_id = None

            raise ArtifactStoreError(
                "Disk full while writing to artifact_store_root",
                details={
                    "cause": "ENOSPC",
                    "src": str(src),
                    "dest": str(dest),
                    "log_ref_id": log_ref_id,
                },
            ) from exc

        size = dest.stat().st_size
        checksum = sha256_file(dest)
        checksums = [ArtifactChecksum(algorithm="sha256", value=checksum)]

        meta = extract_image_metadata(dest) if artifact_type == "BioImageRef" else {}

        ref = ArtifactRef(
            ref_id=ref_id,
            type=artifact_type,
            uri=dest.absolute().as_uri(),
            format=format,
            mime_type=_guess_mime_type(artifact_type, format),
            size_bytes=size,
            checksums=checksums,
            created_at=ArtifactRef.now(),
            metadata=meta,
        )
        self._persist(ref)
        return ref

    def import_directory(self, src: Path, *, artifact_type: str, format: str) -> ArtifactRef:
        assert_path_allowed("read", src, self._config)

        ref_id = uuid.uuid4().hex
        dest = self._artifact_path(ref_id)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(src, dest)
        except OSError as exc:
            if exc.errno != errno.ENOSPC:
                raise

            log_ref_id = None
            try:
                log_ref_id = self.write_log(
                    f"Disk full while importing directory artifact from {src} to {dest}: {exc}"
                ).ref_id
            except Exception:  # noqa: BLE001
                log_ref_id = None

            raise ArtifactStoreError(
                "Disk full while writing to artifact_store_root",
                details={
                    "cause": "ENOSPC",
                    "src": str(src),
                    "dest": str(dest),
                    "log_ref_id": log_ref_id,
                },
            ) from exc

        checksum = sha256_tree(dest)
        checksums = [ArtifactChecksum(algorithm="sha256-tree", value=checksum)]

        size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
        ref = ArtifactRef(
            ref_id=ref_id,
            type=artifact_type,
            uri=dest.absolute().as_uri(),
            format=format,
            mime_type=_guess_mime_type(artifact_type, format),
            size_bytes=size,
            checksums=checksums,
            created_at=ArtifactRef.now(),
            metadata={},
        )
        self._persist(ref)
        return ref

    def _persist(self, ref: ArtifactRef) -> None:
        self._conn.execute(
            """
            INSERT INTO artifacts(
                ref_id,
                type,
                uri,
                format,
                mime_type,
                size_bytes,
                checksums_json,
                metadata_json,
                created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ref.ref_id,
                ref.type,
                ref.uri,
                ref.format,
                ref.mime_type,
                ref.size_bytes,
                json.dumps([c.model_dump() for c in ref.checksums]),
                json.dumps(ref.metadata),
                ref.created_at,
            ),
        )
        self._conn.commit()

    def get(self, ref_id: str) -> ArtifactRef:
        row = self._conn.execute(
            "SELECT ref_id, type, uri, format, mime_type, size_bytes, "
            "checksums_json, metadata_json, created_at "
            "FROM artifacts WHERE ref_id = ?",
            (ref_id,),
        ).fetchone()
        if row is None:
            raise KeyError(ref_id)
        checksums = [ArtifactChecksum(**c) for c in json.loads(row["checksums_json"])]
        return ArtifactRef(
            ref_id=row["ref_id"],
            type=row["type"],
            uri=row["uri"],
            format=row["format"],
            mime_type=row["mime_type"],
            size_bytes=int(row["size_bytes"]),
            checksums=checksums,
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def get_payload(self, ref_id: str) -> dict:
        return {"ref": self.get(ref_id).model_dump()}

    def export(self, ref_id: str, dest_path: Path) -> Path:
        dest_path = assert_path_allowed("write", dest_path, self._config)
        ref = self.get(ref_id)
        src_path = Path(ref.uri.replace("file://", ""))

        if src_path.is_dir():
            if dest_path.exists():
                raise FileExistsError(dest_path)
            shutil.copytree(src_path, dest_path)
            exported_checksum = sha256_tree(dest_path)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            exported_checksum = sha256_file(dest_path)

        recorded = ref.checksums[0].value if ref.checksums else None
        if recorded and exported_checksum != recorded:
            raise ValueError("Exported artifact checksum mismatch")

        return dest_path

    def write_log(self, content: str) -> ArtifactRef:
        ref_id = uuid.uuid4().hex
        dest = self._artifact_path(ref_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

        size = dest.stat().st_size
        checksum = sha256_file(dest)
        checksums = [ArtifactChecksum(algorithm="sha256", value=checksum)]

        ref = ArtifactRef(
            ref_id=ref_id,
            type="LogRef",
            uri=dest.absolute().as_uri(),
            format="text",
            mime_type=_guess_mime_type("LogRef", "text"),
            size_bytes=size,
            checksums=checksums,
            created_at=ArtifactRef.now(),
            metadata={},
        )
        self._persist(ref)
        return ref
