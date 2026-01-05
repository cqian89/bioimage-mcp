from __future__ import annotations

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.errors import ArtifactStoreError


class ArtifactsService:
    def __init__(self, store: ArtifactStore):
        self._store = store

    def artifact_info(self, ref_id: str, text_preview_bytes: int | None = None) -> dict:
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

        # Add image-specific metadata
        if ref.type in ("BioImageRef", "LabelImageRef"):
            response["dims"] = ref.dims
            response["ndim"] = ref.ndim
            response["dtype"] = ref.metadata.get("dtype")
            response["shape"] = ref.metadata.get("shape")

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
