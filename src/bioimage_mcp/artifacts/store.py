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
    """Guess MIME type from artifact type and format.

    For NativeOutputRef and unknown formats, falls back to application/octet-stream
    to support the open/extensible format field (T048/T049).
    """
    if artifact_type == "LogRef":
        return "text/plain"

    fmt_lower = fmt.lower()

    # Handle common image formats
    if fmt_lower in {"ome-zarr", "zarr"}:
        return "application/zarr+ome"
    if fmt_lower in {"ome-tiff", "tiff", "tif"}:
        return "image/tiff"

    # Handle NativeOutputRef format hints (extensible)
    if artifact_type == "NativeOutputRef":
        if "json" in fmt_lower:
            return "application/json"
        if "npy" in fmt_lower:
            return "application/x-npy"

    # Default fallback for unknown formats
    return "application/octet-stream"


def _guess_storage_type_for_directory(src: Path, fmt: str) -> str:
    fmt_lower = fmt.lower()
    if fmt_lower in {"ome-zarr", "zarr"} or src.name.lower().endswith(".zarr"):
        return "zarr-temp"
    return "file"


class ArtifactStore:
    def __init__(self, config: Config, *, conn: sqlite3.Connection | None = None):
        self._config = config
        self._owns_conn = conn is None
        self._conn: sqlite3.Connection = conn or connect(config)

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _objects_dir(self) -> Path:
        return self._config.artifact_store_root / "objects"

    def _artifact_path(self, ref_id: str) -> Path:
        return self._objects_dir() / ref_id

    def import_file(self, src: Path, *, artifact_type: str, format: str) -> ArtifactRef:
        src = src.expanduser().absolute()

        # Clear error for missing files (T023)
        if not src.exists():
            raise FileNotFoundError(f"Cannot import artifact: source file not found at {src}")

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

        # Extract image metadata for image artifact types
        meta = {}
        if artifact_type in {"BioImageRef", "LabelImageRef"}:
            meta = extract_image_metadata(dest)

        ref = ArtifactRef(
            ref_id=ref_id,
            type=artifact_type,
            uri=dest.absolute().as_uri(),
            format=format,
            storage_type="file",
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
        storage_type = _guess_storage_type_for_directory(src, format)
        ref = ArtifactRef(
            ref_id=ref_id,
            type=artifact_type,
            uri=dest.absolute().as_uri(),
            format=format,
            storage_type=storage_type,
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
                storage_type,
                mime_type,
                size_bytes,
                checksums_json,
                metadata_json,
                created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ref.ref_id,
                ref.type,
                ref.uri,
                ref.format,
                ref.storage_type,
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
            "SELECT ref_id, type, uri, format, storage_type, mime_type, size_bytes, "
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
            storage_type=row["storage_type"],
            mime_type=row["mime_type"],
            size_bytes=int(row["size_bytes"]),
            checksums=checksums,
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def get_payload(self, ref_id: str) -> dict:
        """Get artifact payload as a dict with ref metadata.

        Returns dict with 'ref' key containing the ArtifactRef data.
        """
        return {"ref": self.get(ref_id).model_dump()}

    def get_raw_content(self, ref_id: str) -> bytes:
        """Read and return the raw content of an artifact file.

        Returns bytes for the artifact file content.
        Raises ValueError for directory artifacts.
        """
        ref = self.get(ref_id)
        src_path = Path(ref.uri.replace("file://", ""))
        if src_path.is_dir():
            raise ValueError(f"Cannot get raw content for directory artifact: {ref_id}")
        return src_path.read_bytes()

    def parse_native_output(self, ref_id: str) -> dict:
        """Parse a NativeOutputRef JSON artifact (T028).

        Loads and parses a workflow-record-json or similar JSON artifact.
        Used primarily for workflow replay functionality.

        Args:
            ref_id: Reference ID of the NativeOutputRef artifact

        Returns:
            Parsed JSON content as a dict

        Raises:
            KeyError: If artifact not found
            ValueError: If artifact is not a valid JSON NativeOutputRef
        """
        ref = self.get(ref_id)
        if ref.type != "NativeOutputRef":
            raise ValueError(f"Expected NativeOutputRef, got {ref.type}")

        content = self.get_raw_content(ref_id).decode("utf-8")
        return json.loads(content)

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

    def write_native_output(
        self,
        content: str | bytes | dict,
        *,
        format: str,
        metadata: dict | None = None,
    ) -> ArtifactRef:
        """Write a native output artifact (NativeOutputRef).

        This helper is used for:
        - Workflow record JSON (format: workflow-record-json)
        - Tool-specific bundles (format: cellpose-seg-npy, etc.)

        Args:
            content: The content to write (str/bytes/dict - dict will be JSON-encoded)
            format: The format identifier (open/extensible, tool-dependent)
            metadata: Optional metadata dict

        Returns:
            ArtifactRef with type=NativeOutputRef
        """
        ref_id = uuid.uuid4().hex
        dest = self._artifact_path(ref_id)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Handle different content types
        if isinstance(content, dict):
            dest.write_text(json.dumps(content, indent=2, default=str))
        elif isinstance(content, bytes):
            dest.write_bytes(content)
        else:
            dest.write_text(str(content))

        size = dest.stat().st_size
        checksum = sha256_file(dest)
        checksums = [ArtifactChecksum(algorithm="sha256", value=checksum)]

        # Determine mime type from format
        mime_type = "application/octet-stream"
        if "json" in format.lower():
            mime_type = "application/json"
        elif "npy" in format.lower():
            mime_type = "application/x-npy"

        ref = ArtifactRef(
            ref_id=ref_id,
            type="NativeOutputRef",
            uri=dest.absolute().as_uri(),
            format=format,
            mime_type=mime_type,
            size_bytes=size,
            checksums=checksums,
            created_at=ArtifactRef.now(),
            metadata=metadata or {},
        )
        self._persist(ref)
        return ref
