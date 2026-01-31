"""Response serialization for MCP run tool with verbosity control."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)


class RunResponseSerializer:
    """Verbosity-aware serializer for MCP run tool responses."""

    VERBOSITY_LEVELS = ("minimal", "standard", "full")

    def serialize(
        self,
        result: dict[str, Any],
        *,
        id: str,
        verbosity: Literal["minimal", "standard", "full"] | str = "minimal",
    ) -> dict[str, Any]:
        """Serialize a run result with the specified verbosity level."""
        # Validate verbosity - coerce invalid values to minimal (token-safe default)
        if verbosity not in self.VERBOSITY_LEVELS:
            logger.warning(
                f"Invalid verbosity '{verbosity}', coercing to 'minimal' for token safety"
            )
            verbosity = "minimal"

        # Top-level fields: run_id, status, fn_id, outputs
        serialized = {
            "run_id": result["run_id"],
            "status": result["status"],
            "fn_id": id,
            "outputs": {},
        }

        # Handle outputs - filter workflow_record from outputs in minimal/standard
        outputs = result.get("outputs", {})
        for key, artifact in outputs.items():
            # Skip workflow_record output unless full verbosity
            if key == "workflow_record" and verbosity != "full":
                continue

            # Sanitize artifact to remove summary/content (all verbosity levels)
            sanitized = self._sanitize_artifact(artifact)

            if verbosity == "minimal":
                serialized["outputs"][key] = self._artifact_minimal(sanitized)
            elif verbosity == "standard":
                serialized["outputs"][key] = self._artifact_standard(sanitized)
            else:  # full
                serialized["outputs"][key] = sanitized

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

        # error and hints (SC-001) - always include if status is failed
        if result.get("error"):
            serialized["error"] = result["error"]
        if result.get("hints"):
            serialized["hints"] = result["hints"]

        return serialized

    def _sanitize_artifact(self, ref_dict: dict[str, Any]) -> dict[str, Any]:
        """Remove summary and content fields from artifact dict.

        These are never included in run responses per spec:
        - summary: redundant with flattened minimal fields
        - content: prevents token explosion from inline log content
        """
        sanitized = dict(ref_dict)
        sanitized.pop("summary", None)
        sanitized.pop("content", None)
        return sanitized

    def _extract_dimension_field(self, ref_dict: dict[str, Any], field: str) -> Any:
        """Extract a dimension field from metadata, top-level, or summary (in order).

        After ArtifactRef cleanup, dimension fields live in metadata.
        This helper provides backward compatibility during transition.
        """
        metadata = ref_dict.get("metadata", {})
        summary = ref_dict.get("summary", {})

        # Order of preference: metadata > top-level > summary
        value = metadata.get(field) or ref_dict.get(field) or summary.get(field)

        return value

    def _normalize_dims(self, dims: Any) -> list[str] | None:
        """Normalize dims to a list of strings.

        Handles:
        - list: ["T", "C", "Z", "Y", "X"] -> unchanged
        - string: "TCZYX" -> ["T", "C", "Z", "Y", "X"]
        - None: -> None
        """
        if dims is None:
            return None
        if isinstance(dims, list):
            return dims
        if isinstance(dims, str):
            return list(dims)
        return None

    def _artifact_minimal(self, ref_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract minimal artifact summary for LLM chaining."""
        # Extract dimension fields from metadata (primary) or fallbacks
        shape = self._extract_dimension_field(ref_dict, "shape")
        dims = self._normalize_dims(self._extract_dimension_field(ref_dict, "dims"))
        dtype = self._extract_dimension_field(ref_dict, "dtype")
        physical_pixel_sizes = self._extract_dimension_field(ref_dict, "physical_pixel_sizes")
        channel_names = self._extract_dimension_field(ref_dict, "channel_names")

        minimal = {
            "ref_id": ref_dict["ref_id"],
            "type": ref_dict["type"],
            "shape": shape,
            "dims": dims,
            "dtype": dtype,
            "size_mb": self._size_mb(ref_dict.get("size_bytes")),
        }

        # Optional fields allowed in minimal
        if physical_pixel_sizes is not None:
            minimal["physical_pixel_sizes"] = physical_pixel_sizes
        if ref_dict.get("format"):
            minimal["format"] = ref_dict["format"]
        if channel_names is not None:
            minimal["channel_names"] = self._maybe_truncate_channel_names(channel_names)

        # uri included in minimal for connectivity (Constitution III)
        minimal["uri"] = ref_dict.get("uri")

        # Remove None values for cleaner output
        return {k: v for k, v in minimal.items() if v is not None}

    def _artifact_standard(self, ref_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract standard artifact with trimmed metadata.

        Standard includes: ref_id, type, uri, format, storage_type, size_bytes,
        size_mb, metadata (stripped). Plus dimension fields from minimal.
        """
        # Extract dimension fields from metadata (primary) or fallbacks
        shape = self._extract_dimension_field(ref_dict, "shape")
        dims = self._normalize_dims(self._extract_dimension_field(ref_dict, "dims"))
        dtype = self._extract_dimension_field(ref_dict, "dtype")
        physical_pixel_sizes = self._extract_dimension_field(ref_dict, "physical_pixel_sizes")
        channel_names = self._extract_dimension_field(ref_dict, "channel_names")

        standard = {
            "ref_id": ref_dict["ref_id"],
            "type": ref_dict["type"],
            "uri": ref_dict.get("uri"),
            "format": ref_dict.get("format"),
            "storage_type": ref_dict.get("storage_type"),
            "size_bytes": ref_dict.get("size_bytes"),
            "size_mb": self._size_mb(ref_dict.get("size_bytes")),
            "shape": shape,
            "dims": dims,
            "dtype": dtype,
        }

        # Add physical_pixel_sizes and channel_names if present
        if physical_pixel_sizes is not None:
            standard["physical_pixel_sizes"] = physical_pixel_sizes
        if channel_names is not None:
            standard["channel_names"] = channel_names

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


class DescribeResponseSerializer:
    """Verbosity-aware serializer for MCP describe tool responses."""

    VERBOSITY_LEVELS = ("minimal", "standard", "full")

    def serialize(
        self,
        result: dict[str, Any],
        *,
        verbosity: Literal["minimal", "standard", "full"] | str = "minimal",
    ) -> dict[str, Any]:
        """Serialize a describe result with the specified verbosity level."""
        # Validate verbosity - coerce invalid values to minimal (token-safe default)
        if verbosity not in self.VERBOSITY_LEVELS:
            logger.warning(
                f"Invalid verbosity '{verbosity}', coercing to 'minimal' for token safety"
            )
            verbosity = "minimal"

        if verbosity in ("standard", "full"):
            return result

        # Minimal verbosity

        # Handle batch responses
        if "schemas" in result and "errors" in result:
            return {
                "schemas": {
                    fn_id: self._serialize_single(schema)
                    for fn_id, schema in result["schemas"].items()
                },
                "errors": result["errors"],
            }

        # Handle single error response
        if "error" in result and len(result) == 1:
            return result

        return self._serialize_single(result)

    def _serialize_single(self, result: dict[str, Any]) -> dict[str, Any]:
        """Serialize a single describe result for minimal verbosity."""
        # Core fields only: id, type, summary, inputs, outputs, params_schema
        # Omit 'hints', 'name', 'tags', etc.
        serialized: dict[str, Any] = {}

        # Explicitly allowed core fields
        for field in ("id", "type", "summary", "inputs", "outputs"):
            if field in result:
                serialized[field] = result[field]

        # Handle params_schema with description stripping
        if "params_schema" in result:
            params_schema = result["params_schema"]
            if isinstance(params_schema, dict):
                serialized["params_schema"] = self._strip_property_descriptions(params_schema)
            else:
                serialized["params_schema"] = params_schema

        return serialized

    def _strip_property_descriptions(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Strip 'description' field from each property in params_schema['properties']."""
        new_schema = dict(schema)
        if "properties" in new_schema and isinstance(new_schema["properties"], dict):
            new_properties = {}
            for k, v in new_schema["properties"].items():
                if isinstance(v, dict):
                    new_v = dict(v)
                    new_v.pop("description", None)
                    new_properties[k] = new_v
                else:
                    new_properties[k] = v
            new_schema["properties"] = new_properties
        return new_schema
