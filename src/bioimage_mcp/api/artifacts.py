from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.preview import (
    generate_image_preview,
    generate_label_preview,
    generate_table_preview,
)
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.errors import ArtifactStoreError


class ArtifactsService:
    def __init__(self, store: ArtifactStore):
        self._store = store

    def artifact_info(
        self,
        ref_id: str,
        text_preview_bytes: int | None = None,
        include_image_preview: bool = False,
        image_preview_size: int = 256,
        channels: int | list[int] | None = None,
        projection: str | dict = "max",
        slice_indices: dict | None = None,
        include_table_preview: bool = False,
        preview_rows: int = 5,
        preview_columns: int | None = None,
    ) -> dict:
        """Get full metadata and optional text preview for an artifact."""
        try:
            ref = self._store.get(ref_id)
        except KeyError:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Artifact {ref_id} not found",
                    "details": [
                        {
                            "path": "/ref_id",
                            "expected": "valid artifact reference ID",
                            "actual": ref_id,
                            "hint": "Use artifact references from prior tool outputs or imports",
                        }
                    ],
                }
            }

        # Check for expired memory artifacts
        if ref.storage_type == "memory":
            sim_path = ref.metadata.get("_simulated_path")
            if sim_path and not Path(sim_path).exists():
                return {
                    "error": {
                        "code": "OBJECT_REF_EXPIRED",
                        "message": f"ObjectRef {ref_id} is no longer accessible",
                        "details": [
                            {
                                "path": "/ref_id",
                                "hint": (
                                    "Object references are session-scoped and "
                                    "expire when the session ends"
                                ),
                            }
                        ],
                    }
                }

        response = {
            "ref_id": ref.ref_id,
            "type": ref.type,
            "uri": ref.uri,
            "mime_type": ref.mime_type,
            "size_bytes": ref.size_bytes,
            "checksums": [c.model_dump() for c in ref.checksums],
        }

        # Add ObjectRef specific metadata
        if ref.type in ("ObjectRef", "GroupByRef", "FigureRef", "AxesRef", "AxesImageRef"):
            # Add native_type from python_class
            if hasattr(ref, "python_class") and ref.python_class:
                response["native_type"] = ref.python_class

            # Add object_preview
            if ref.storage_type == "memory":
                sim_path = ref.metadata.get("_simulated_path")
                if sim_path:
                    try:
                        import pickle

                        with open(sim_path, "rb") as f:
                            obj = pickle.load(f)
                        obj_repr = repr(obj)
                        if len(obj_repr) > 500:
                            obj_repr = obj_repr[:497] + "..."
                        response["object_preview"] = obj_repr
                    except Exception:  # noqa: BLE001
                        # Omit the field on any exception
                        pass
                else:
                    response["object_preview"] = "In-memory object (not serialized)"

        # Add image-specific metadata (read from metadata dict after model cleanup)
        if ref.type in ("BioImageRef", "LabelImageRef"):
            response["dims"] = ref.metadata.get("dims")
            response["ndim"] = ref.metadata.get("ndim")
            response["dtype"] = ref.metadata.get("dtype")
            response["shape"] = ref.metadata.get("shape")

            # Generate image preview if requested
            if include_image_preview:
                # Extract path from URI (handle file:// prefix)
                # BioImage handles URIs, but we might need a local path for some operations
                # or if the URI is not standard.
                uri = ref.uri
                if uri.startswith("file://"):
                    path = Path(uri.replace("file://", ""))
                elif uri.startswith("mem://"):
                    # For memory artifacts, we might have a _simulated_path
                    sim_path = ref.metadata.get("_simulated_path")
                    if sim_path:
                        path = Path(sim_path)
                    else:
                        path = None
                else:
                    path = None

                if path and path.exists():
                    # Handle channel selection:
                    # - If channels is int, use that channel index
                    # - If channels is list, use first element
                    # - If None and image has C axis, use channel 0
                    #   (handled by generate_image_preview)
                    channel_idx = None
                    if isinstance(channels, int):
                        channel_idx = channels
                    elif isinstance(channels, list) and channels:
                        channel_idx = channels[0]

                    if ref.type == "LabelImageRef":
                        preview = generate_label_preview(
                            path=path,
                            dims=response.get("dims"),
                            shape=response.get("shape"),
                            dtype=response.get("dtype"),
                            max_size=image_preview_size,
                            projection=projection,
                            slice_indices=slice_indices,
                            channel=channel_idx,
                        )
                    else:
                        preview = generate_image_preview(
                            path=path,
                            dims=response.get("dims"),
                            shape=response.get("shape"),
                            dtype=response.get("dtype"),
                            max_size=image_preview_size,
                            projection=projection,
                            slice_indices=slice_indices,
                            channel=channel_idx,
                        )

                    if preview:
                        response["image_preview"] = preview

        # Add table-specific metadata and preview
        if ref.type == "TableRef":
            response["total_rows"] = getattr(ref, "row_count", None)
            cols = getattr(ref, "columns", [])
            if not cols and ref.metadata.get("columns"):
                cols = [c.get("name") for c in ref.metadata.get("columns", [])]
            response["total_columns"] = len(cols)

            if include_table_preview:
                uri = ref.uri
                if uri.startswith("file://"):
                    path = Path(uri.replace("file://", ""))
                    if path.exists():
                        preview = generate_table_preview(
                            path, preview_rows=preview_rows, preview_columns=preview_columns
                        )
                        if preview:
                            response["table_preview"] = preview.get("table_preview")
                            # Use metadata columns for high-fidelity dtypes if available
                            if hasattr(ref.metadata, "columns") and ref.metadata.columns:
                                response["dtypes"] = {c.name: c.dtype for c in ref.metadata.columns}
                            else:
                                response["dtypes"] = preview.get("dtypes")

        # Add text preview if requested and safe
        if text_preview_bytes is not None and self._is_safe_text_type(ref.mime_type):
            try:
                # We use get_raw_content which handles file-based artifacts
                content = self._store.get_raw_content(ref_id)
                response["text_preview"] = content[:text_preview_bytes].decode(
                    "utf-8", errors="replace"
                )
            except (ValueError, ArtifactStoreError, UnicodeDecodeError):
                # Fallback for errors reading content or decoding
                response["text_preview"] = None
        elif text_preview_bytes is not None:
            response["text_preview"] = None

        return response

    def _is_safe_text_type(self, mime_type: str) -> bool:
        """Check if a MIME type is safe for text preview."""
        safe_types = {
            "text/plain",
            "application/json",
            "text/csv",
        }
        return mime_type in safe_types
