"""Response serialization for MCP run tool with verbosity control."""

from __future__ import annotations

from typing import Any, Literal


class RunResponseSerializer:
    """Verbosity-aware serializer for MCP run tool responses."""

    VERBOSITY_LEVELS = ("minimal", "standard", "full")

    def serialize(
        self,
        result: dict[str, Any],
        *,
        fn_id: str,
        verbosity: Literal["minimal", "standard", "full"] = "minimal",
    ) -> dict[str, Any]:
        """Serialize a run result with the specified verbosity level."""
        # Top-level fields: run_id, status, fn_id, outputs
        serialized = {
            "run_id": result["run_id"],
            "status": result["status"],
            "fn_id": fn_id,
            "outputs": {},
        }

        # Handle outputs
        outputs = result.get("outputs", {})
        for key, artifact in outputs.items():
            if verbosity == "minimal":
                serialized["outputs"][key] = self._artifact_minimal(artifact)
            elif verbosity == "standard":
                serialized["outputs"][key] = self._artifact_standard(artifact)
            else:  # full
                serialized["outputs"][key] = artifact

        # warnings only if non-empty
        warnings = result.get("warnings", [])
        if warnings:
            serialized["warnings"] = warnings

        # log_ref only if status != "success" OR verbosity == "full"
        log_ref = result.get("log_ref")
        if log_ref and (result["status"] != "success" or verbosity == "full"):
            serialized["log_ref"] = log_ref

        # workflow_record only if verbosity == "full"
        workflow_record = result.get("workflow_record")
        if workflow_record and verbosity == "full":
            serialized["workflow_record"] = workflow_record

        return serialized

    def _artifact_minimal(self, ref_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract minimal artifact summary for LLM chaining."""
        minimal = {
            "ref_id": ref_dict["ref_id"],
            "type": ref_dict["type"],
            "shape": ref_dict.get("shape"),
            "dims": ref_dict.get("dims"),
            "dtype": ref_dict.get("dtype"),
            "size_mb": self._size_mb(ref_dict.get("size_bytes")),
        }

        # Optional fields allowed in minimal
        for field in ("physical_pixel_sizes", "format"):
            if field in ref_dict:
                minimal[field] = ref_dict[field]

        if "channel_names" in ref_dict:
            minimal["channel_names"] = self._maybe_truncate_channel_names(ref_dict["channel_names"])

        # uri only if memory-backed
        if self._is_memory_artifact(ref_dict):
            minimal["uri"] = ref_dict["uri"]

        # Remove None values for cleaner output
        return {k: v for k, v in minimal.items() if v is not None}

    def _artifact_standard(self, ref_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract standard artifact with trimmed metadata.

        Standard includes: ref_id, type, uri, format, storage_type, size_bytes,
        size_mb, metadata (stripped). Plus dimension fields from minimal.
        """
        standard = {
            "ref_id": ref_dict["ref_id"],
            "type": ref_dict["type"],
            "uri": ref_dict.get("uri"),
            "format": ref_dict.get("format"),
            "storage_type": ref_dict.get("storage_type"),
            "size_bytes": ref_dict.get("size_bytes"),
            "size_mb": self._size_mb(ref_dict.get("size_bytes")),
            "shape": ref_dict.get("shape"),
            "dims": ref_dict.get("dims"),
            "dtype": ref_dict.get("dtype"),
        }

        # Add physical_pixel_sizes and channel_names if present
        for field in ("physical_pixel_sizes", "channel_names"):
            if field in ref_dict:
                standard[field] = ref_dict[field]

        # metadata (stripped)
        if "metadata" in ref_dict:
            standard["metadata"] = self._strip_file_metadata(ref_dict["metadata"])

        # Exclude checksums, created_at, workflow_record handled by being omitted here
        return {k: v for k, v in standard.items() if v is not None}

    def _strip_file_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Remove file_metadata from metadata dict."""
        return {k: v for k, v in metadata.items() if k != "file_metadata"}

    def _maybe_truncate_channel_names(self, names: list[str]) -> list[str]:
        """Truncate channel names to 10 items max."""
        if len(names) > 10:
            truncated = names[:10]
            truncated.append(f"...+{len(names) - 10} more")
            return truncated
        return names

    def _size_mb(self, size_bytes: int | None) -> float | None:
        """Convert bytes to MB, rounded to 2 decimal places."""
        if size_bytes is None:
            return None
        return round(size_bytes / 1_048_576, 2)

    def _is_memory_artifact(self, ref_dict: dict[str, Any]) -> bool:
        """Check if artifact is memory-backed."""
        storage_type = ref_dict.get("storage_type")
        uri = ref_dict.get("uri", "")
        return storage_type == "memory" or uri.startswith("mem://") or uri.startswith("obj://")
