from __future__ import annotations

import errno
import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Literal

from bioimage_mcp.api.permissions import PermissionService
from bioimage_mcp.artifacts.checksums import sha256_file, sha256_tree
from bioimage_mcp.artifacts.memory import MemoryArtifactStore
from bioimage_mcp.artifacts.metadata import (
    extract_image_metadata,
    extract_table_metadata,
    get_ndim,
)
from bioimage_mcp.artifacts.models import (
    ArtifactChecksum,
    ArtifactRef,
    PlotMetadata,
    PlotRef,
)
from bioimage_mcp.config.fs_policy import assert_path_allowed
from bioimage_mcp.config.schema import Config, OverwritePolicy
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
    if fmt_lower == "png":
        return "image/png"
    if fmt_lower == "svg":
        return "image/svg+xml"

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
    def __init__(
        self,
        config: Config,
        *,
        conn: sqlite3.Connection | None = None,
        memory_store: MemoryArtifactStore | None = None,
    ):
        self._config = config
        self._owns_conn = conn is None
        self._conn: sqlite3.Connection = conn or connect(config)
        self._memory_store = memory_store or MemoryArtifactStore()

    def resolve_memory_artifact(self, ref_id: str) -> ArtifactRef | None:
        """Resolve a mem:// artifact from the memory store."""
        return self._memory_store.get(ref_id)

    def create_memory_artifact_ref(
        self,
        session_id: str,
        env_id: str,
        artifact_id: str,
        artifact_type: str,
        format: str,
        shape: tuple[int, ...] | list[int],
        dims: list[str],
        dtype: str,
        metadata: dict | None = None,
    ) -> ArtifactRef:
        """Create a memory-backed artifact reference with dimension metadata.

        Used by workers to record outputs that remain in memory.
        """
        uri = f"mem://{session_id}/{env_id}/{artifact_id}"

        # Merge provided metadata with dimension info
        full_metadata = (metadata or {}).copy()
        full_metadata.update(
            {
                "shape": list(shape),
                "ndim": len(shape),
                "dims": dims,
                "dtype": str(dtype),
            }
        )

        ref = ArtifactRef(
            ref_id=artifact_id,
            type=artifact_type,
            uri=uri,
            format=format,
            storage_type="memory",
            mime_type=_guess_mime_type(artifact_type, format),
            size_bytes=0,  # Memory artifacts don't have a file size yet
            created_at=ArtifactRef.now(),
            metadata=full_metadata,
            ndim=len(shape),
            dims=dims,
        )
        # Note: We don't persist memory artifacts in SQLite as they are transient
        return ref

    def is_memory_artifact(self, uri: str) -> bool:
        """Check if a URI is a memory artifact."""
        return uri.startswith("mem://")

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

    def import_file(
        self,
        src: Path,
        *,
        artifact_type: str,
        format: str,
        metadata_override: dict | None = None,
    ) -> ArtifactRef:
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
        # Use src instead of dest because src has the correct file extension (T020 fix)
        meta = {}
        ndim = None
        dims = None
        physical_pixel_sizes = None

        if artifact_type in {"BioImageRef", "LabelImageRef"}:
            meta = extract_image_metadata(src) or {}
            if meta:
                ndim = get_ndim(meta)
                dims = meta.get("dims")
                physical_pixel_sizes = meta.get("physical_pixel_sizes")
        elif artifact_type == "TableRef":
            meta = extract_table_metadata(src) or {}

        # Apply metadata override (T048)
        if metadata_override:
            meta.update(metadata_override)
            if "ndim" in metadata_override:
                ndim = metadata_override["ndim"]
            if "dims" in metadata_override:
                dims = metadata_override["dims"]
            if "physical_pixel_sizes" in metadata_override:
                physical_pixel_sizes = metadata_override["physical_pixel_sizes"]

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
            ndim=ndim,
            dims=dims,
            physical_pixel_sizes=physical_pixel_sizes,
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

        # Extract metadata for directory-based artifacts (e.g. OME-Zarr) (T028)
        meta = {}
        ndim = None
        dims = None
        physical_pixel_sizes = None

        if artifact_type in {"BioImageRef", "LabelImageRef"} and storage_type == "zarr-temp":
            meta = extract_image_metadata(src) or {}
            if meta:
                ndim = get_ndim(meta)
                dims = meta.get("dims")
                physical_pixel_sizes = meta.get("physical_pixel_sizes")

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
            metadata=meta,
            ndim=ndim,
            dims=dims,
            physical_pixel_sizes=physical_pixel_sizes,
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
        # Try memory store first (T015)
        mem_ref = self.resolve_memory_artifact(ref_id)
        if mem_ref:
            return mem_ref

        row = self._conn.execute(
            "SELECT ref_id, type, uri, format, storage_type, mime_type, size_bytes, "
            "checksums_json, metadata_json, created_at "
            "FROM artifacts WHERE ref_id = ?",
            (ref_id,),
        ).fetchone()
        if row is None:
            raise KeyError(ref_id)
        checksums = [ArtifactChecksum(**c) for c in json.loads(row["checksums_json"])]
        metadata = json.loads(row["metadata_json"])
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
            metadata=metadata,
            ndim=metadata.get("ndim"),
            dims=metadata.get("dims"),
            physical_pixel_sizes=metadata.get("physical_pixel_sizes"),
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
        if self.is_memory_artifact(ref.uri):
            # T016 simulation: check for _simulated_path
            sim_path = ref.metadata.get("_simulated_path")
            if sim_path:
                src_path = Path(sim_path)
            else:
                raise ArtifactStoreError(
                    f"Cannot get raw content for memory artifact {ref_id}: data is in worker memory"
                )
        else:
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

    def export(
        self,
        ref_id: str,
        dest_path: Path,
        *,
        format: str | None = None,
        session: object | None = None,
        permission_service: PermissionService | None = None,
    ) -> Path:
        dest_path = assert_path_allowed(
            "write",
            dest_path,
            self._config,
            session=session,
            permission_service=permission_service,
        )
        ref = self.get(ref_id)

        # Handle format inference if not provided
        if format is None:
            # Hint from destination extension
            suffix = dest_path.name.lower()
            if suffix.endswith(".png"):
                format = "PNG"
            elif suffix.endswith(".csv"):
                format = "CSV"
            elif suffix.endswith(".ome.zarr") or suffix.endswith(".zarr"):
                format = "OME-Zarr"
            elif suffix.endswith(".ome.tiff") or suffix.endswith(".ome.tif"):
                format = "OME-TIFF"
            elif suffix.endswith(".tif") or suffix.endswith(".tiff"):
                # For .tif/.tiff, we still infer between PNG and OME-TIFF
                # but OME-TIFF is a safer bet for these extensions
                format = "OME-TIFF"

        if format is None:
            from bioimage_mcp.artifacts.export import infer_export_format

            format = infer_export_format(ref)

        if self.is_memory_artifact(ref.uri):
            # T016 simulation: check for _simulated_path in metadata
            sim_path = ref.metadata.get("_simulated_path")
            if sim_path:
                src_path = Path(sim_path)
            else:
                raise ArtifactStoreError(
                    f"Cannot export memory artifact {ref_id}: data is not on the server. "
                    "Memory artifacts must be materialized to a file first."
                )
        else:
            src_path = Path(ref.uri.replace("file://", ""))

        if dest_path.exists():
            overwrite_policy = self._config.permissions.on_overwrite
            if overwrite_policy == OverwritePolicy.DENY:
                raise PermissionError(f"Overwrite denied for {dest_path}")
            if overwrite_policy == OverwritePolicy.ASK:
                if permission_service is None:
                    raise PermissionError(f"Overwrite denied for {dest_path}")
                decision = permission_service.elicit_confirmation(
                    dest_path,
                    session=session,
                    config=self._config,
                )
                if decision != "ALLOWED":
                    raise PermissionError(f"Overwrite denied for {dest_path}")

        # If format matches current format, perform simple copy
        if format.upper() == ref.format.upper():
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

        # Perform format conversion
        return self._export_with_conversion(ref, src_path, dest_path, format)

    def _export_with_conversion(
        self, ref: ArtifactRef, src_path: Path, dest_path: Path, format: str
    ) -> Path:
        """Perform format-aware export with conversion."""
        from bioio import BioImage

        format = format.upper()

        # Table export (CSV)
        if format == "CSV" and ref.type == "TableRef":
            # If current format is CSV, it would have been caught by equality check
            # But just in case, or if we support other table formats later.
            shutil.copy2(src_path, dest_path)
            return dest_path

        # Image exports
        def load_image_safe(path, fmt):
            try:
                img = BioImage(path)
                data = img.data
                return data.compute() if hasattr(data, "compute") else data
            except Exception:
                # Try with extension hint if direct load fails (objects/ID has no extension)
                fmt_lower = (fmt or "").lower()
                suffix = ".tif"
                if "zarr" in fmt_lower:
                    suffix = ".ome.zarr"
                elif "tiff" in fmt_lower or "tif" in fmt_lower:
                    suffix = ".ome.tiff"
                elif "png" in fmt_lower:
                    suffix = ".png"

                import tempfile

                # Create a temporary symlink with extension
                tmp_dir = Path(tempfile.mkdtemp())
                try:
                    tmp_file = tmp_dir / f"image{suffix}"
                    if path.is_dir():
                        os.symlink(path, tmp_file, target_is_directory=True)
                    else:
                        os.symlink(path, tmp_file)

                    img = BioImage(tmp_file)
                    data = img.data
                    return data.compute() if hasattr(data, "compute") else data
                finally:
                    try:
                        shutil.rmtree(tmp_dir)
                    except Exception:
                        pass

        data = load_image_safe(src_path, ref.format)

        if format == "PNG":
            import numpy as np
            from PIL import Image

            if data.ndim > 2:
                data = np.squeeze(data)
                if data.ndim != 2:
                    raise ValueError(f"PNG export requires 2D data, got {data.ndim}D")
            Image.fromarray(data).save(dest_path)

        elif format == "OME-TIFF":
            import numpy as np
            from bioio.writers import OmeTiffWriter

            while data.ndim < 5:
                data = np.expand_dims(data, axis=0)
            OmeTiffWriter.save(data, str(dest_path), dim_order="TCZYX")

        elif format == "OME-ZARR":
            from bioio_ome_zarr.writers import OMEZarrWriter

            dims = ref.metadata.get("dims") or ["T", "C", "Z", "Y", "X"][-data.ndim :]
            axis_type_map = {
                "t": "time",
                "c": "channel",
                "z": "space",
                "y": "space",
                "x": "space",
            }
            axes_names = [d.lower() for d in dims]
            axes_types = [axis_type_map.get(d, "space") for d in axes_names]

            writer = OMEZarrWriter(
                store=str(dest_path),
                level_shapes=[data.shape],
                dtype=data.dtype,
                axes_names=axes_names,
                axes_types=axes_types,
            )
            writer.write_full_volume(data)

        elif format == "NPY":
            import numpy as np

            np.save(dest_path, data)

        else:
            raise ValueError(f"Unsupported export format: {format}")

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


def write_plot(fig, path: Path, dpi: int = 100, plot_type: str | None = None) -> PlotRef:
    """Save a matplotlib figure as a PlotRef artifact.

    Args:
        fig: Matplotlib figure object
        path: Path where to save the figure
        dpi: Dots per inch for the output image
        plot_type: Optional string identifying the type of plot (e.g. "phasor")

    Returns:
        PlotRef artifact pointing to the saved figure
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save figure to path
    # We use bbox_inches="tight" to ensure the plot isn't cut off
    fmt: Literal["PNG", "SVG"] = "PNG"
    if path.suffix.lower() == ".svg":
        fmt = "SVG"

    fig.savefig(path, dpi=dpi, format=fmt.lower(), bbox_inches="tight")

    size = path.stat().st_size
    checksum = sha256_file(path)
    checksums = [ArtifactChecksum(algorithm="sha256", value=checksum)]

    # Get dimensions in pixels
    width_px = int(fig.get_figwidth() * dpi)
    height_px = int(fig.get_figheight() * dpi)

    meta = PlotMetadata(
        width_px=width_px,
        height_px=height_px,
        dpi=dpi,
        plot_type=plot_type,
        title=fig.get_label() or None,
    )

    return PlotRef(
        ref_id=uuid.uuid4().hex,
        type="PlotRef",
        uri=path.absolute().as_uri(),
        format=fmt,
        mime_type="image/png" if fmt == "PNG" else "image/svg+xml",
        size_bytes=size,
        checksums=checksums,
        created_at=ArtifactRef.now(),
        metadata=meta,
    )
