from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.preview import generate_image_preview
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

        response = {
            "ref_id": ref.ref_id,
            "type": ref.type,
            "uri": ref.uri,
            "mime_type": ref.mime_type,
            "size_bytes": ref.size_bytes,
            "checksums": [c.model_dump() for c in ref.checksums],
        }

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
                    # - If None and image has C axis, use channel 0 (handled by generate_image_preview)
                    channel_idx = None
                    if isinstance(channels, int):
                        channel_idx = channels
                    elif isinstance(channels, list) and channels:
                        channel_idx = channels[0]

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
