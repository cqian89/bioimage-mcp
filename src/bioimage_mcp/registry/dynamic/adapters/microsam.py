"""
Adapter for micro_sam functions.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

logger = logging.getLogger(__name__)

# Parameters that are artifact inputs, not schema params
ARTIFACT_INPUT_PARAMS = {
    "image",
    "input",
    "labels",
    "label_image",
    "intensity_image",
    "input_image",
    "source",
    "src",
    "embedding",
    "predictor",
}


class MicrosamAdapter(BaseAdapter):
    """Adapter for exposing micro_sam functions dynamically."""

    def __init__(self) -> None:
        self.introspector = Introspector()

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from micro_sam submodules.

        Args:
            module_config: Configuration dictionary (prefix, modules).

        Returns:
            List of discovered function metadata.
        """
        prefix = module_config.get("prefix", "micro_sam")

        try:
            root_module = importlib.import_module(prefix)
        except ImportError:
            logger.debug(f"Module {prefix} not found, skipping discovery.")
            return []

        results = []

        # Enumerate all submodules of micro_sam
        # walk_packages needs the path(s) to search in and the prefix for the module names
        for _, mod_name, _ in pkgutil.walk_packages(
            root_module.__path__, root_module.__name__ + "."
        ):
            # Exclude micro_sam.sam_annotator and private/test modules
            if "sam_annotator" in mod_name:
                continue
            if ".test" in mod_name or mod_name.split(".")[-1].startswith("_"):
                continue

            try:
                module = importlib.import_module(mod_name)
            except ImportError as e:
                logger.debug(f"Could not import {mod_name}: {e}")
                continue

            for name in dir(module):
                if name.startswith("_"):
                    continue

                obj = getattr(module, name)

                # Expose public functions that are actually defined in this module
                # (Avoid re-exports if possible, but micro_sam might re-export in __init__)
                if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
                    continue

                # Check if it's defined in this module to avoid massive duplication
                # if modules re-export everything from submodules.
                # However, many libraries intentionally re-export at package level.
                # For micro_sam, we want to expose the submodules specifically as requested.
                if getattr(obj, "__module__", None) != mod_name:
                    continue

                # Discovery should exclude methods with **kwargs unless overlay exists (T047)
                try:
                    sig = inspect.signature(obj)
                    if any(
                        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                    ):
                        continue
                except (ValueError, TypeError):
                    pass

                io_pattern = self.resolve_io_pattern(f"{mod_name}.{name}", None)

                meta = self.introspector.introspect(
                    func=obj,
                    source_adapter="microsam",
                    io_pattern=io_pattern,
                )

                # Set fn_id to the fully qualified upstream id
                meta.fn_id = f"{mod_name}.{name}"
                meta.qualified_name = meta.fn_id
                meta.module = mod_name

                results.append(meta)

        return results

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact] | dict[str, Any],
        params: dict[str, Any],
        work_dir: Path | None = None,
        hints: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Execute a discovered micro_sam function.

        Args:
            fn_id: Unique function identifier.
            inputs: List or dict of input artifacts.
            params: Parameter dictionary.
            work_dir: Working directory for output artifacts.
            hints: Optional execution hints.

        Returns:
            List of output artifact references.
        """
        # Handle static/manual functions first
        if fn_id == "micro_sam.cache.clear":
            from bioimage_mcp.registry.dynamic.object_cache import clear

            clear()
            return []

        if fn_id == "micro_sam.compute_embedding":
            return self._execute_compute_embedding(inputs, params)

        if "sam_annotator" in fn_id:
            raise RuntimeError(f"Function {fn_id} is denylisted for headless execution.")

        parts = fn_id.split(".")
        module_path = ".".join(parts[:-1])
        func_name = parts[-1]

        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise RuntimeError(f"Could not resolve function {fn_id}: {e}") from e

        if work_dir is None:
            work_dir = Path(tempfile.gettempdir()) / "microsam"
        work_dir.mkdir(parents=True, exist_ok=True)

        args = []
        kwargs = {}
        param_names = set(inspect.signature(func).parameters.keys())

        # Prompt coercion: convert lists to numpy arrays for specific SAM parameters
        processed_params = params.copy()
        for p_name in [
            "point_coords",
            "point_labels",
            "box",
            "input_points",
            "input_labels",
            "input_box",
        ]:
            if p_name in processed_params:
                val = processed_params[p_name]
                if isinstance(val, list):
                    processed_params[p_name] = np.array(val)

        # Load input images and objects
        input_axes = "YX"
        for name, artifact in self._normalize_inputs(inputs):
            val = self._load_image(artifact)

            if isinstance(val, np.ndarray):
                # Try to extract axes metadata from the primary image
                if isinstance(artifact, dict):
                    input_axes = artifact.get("metadata", {}).get("axes", "YX")
                else:
                    input_axes = getattr(artifact, "metadata", {}) or {}
                    input_axes = input_axes.get("axes", "YX")

            # Match artifact to parameter name if possible
            if name in param_names:
                kwargs[name] = val
            elif "image" in param_names and "image" not in kwargs and isinstance(val, np.ndarray):
                kwargs["image"] = val
            elif (
                "predictor" in param_names
                and "predictor" not in kwargs
                and not isinstance(val, np.ndarray)
            ):
                kwargs["predictor"] = val
            elif (
                "embedding" in param_names
                and "embedding" not in kwargs
                and not isinstance(val, np.ndarray)
            ):
                kwargs["embedding"] = val
            elif not args:
                args.append(val)
            else:
                kwargs[name] = val

        # Execute the function
        try:
            result = func(*args, **kwargs, **processed_params)
        except Exception as e:
            logger.error(f"Error executing {fn_id}: {e}")
            raise

        # Handle output: return LabelImageRef for arrays, ObjectRef for others
        if isinstance(result, np.ndarray):
            # Segmentation result (Labels)
            output_ref = self._save_image(
                result, work_dir, axes=input_axes, artifact_type="LabelImageRef"
            )
            return [output_ref]
        elif result is None:
            return []
        else:
            # Stateful object (Predictor, Embedding, etc.)
            object_id = uuid.uuid4().hex
            OBJECT_CACHE.set(object_id, result)

            # Try to get session info for a cleaner URI if we were in a session context
            # Fallback to simple obj:// ID
            obj_uri = f"obj://{object_id}"

            return [
                {
                    "type": "ObjectRef",
                    "format": "pickle",
                    "ref_id": object_id,
                    "uri": obj_uri,
                    "python_class": f"{type(result).__module__}.{type(result).__name__}",
                    "storage_type": "memory",
                    "metadata": {
                        "module": type(result).__module__,
                        "class": type(result).__name__,
                    },
                }
            ]

    def _normalize_inputs(
        self, inputs: list[Artifact] | dict[str, Any]
    ) -> list[tuple[str, Artifact]]:
        """Standardize inputs into (name, artifact) pairs."""
        normalized: list[tuple[str, Artifact]] = []
        if isinstance(inputs, dict):
            for name, artifact in inputs.items():
                normalized.append((name, artifact))
        else:
            for idx, item in enumerate(inputs):
                if isinstance(item, tuple) and len(item) == 2:
                    name, artifact = item
                else:
                    name = "image" if idx == 0 else f"input_{idx}"
                    artifact = item
                normalized.append((str(name), artifact))
        return normalized

    def _execute_compute_embedding(
        self, inputs: list[Artifact] | dict[str, Any], params: dict[str, Any]
    ) -> list[dict]:
        """Manual implementation for micro_sam.compute_embedding."""
        try:
            from micro_sam import util
        except ImportError as e:
            raise RuntimeError("micro_sam is not installed in this environment.") from e

        normalized = self._normalize_inputs(inputs)
        if not normalized:
            raise ValueError("No input image provided for compute_embedding.")

        image_artifact = normalized[0][1]
        image_data = self._load_image(image_artifact)

        model_type = params.get("model", "vit_b")

        # Resolve device
        from bioimage_mcp_microsam.device import select_device

        device = select_device(params.get("device", "auto"))

        predictor = util.get_sam_model(model_type=model_type, device=device, return_predictor=True)

        # Compute embedding
        # Use util.get_embeddings if we wanted just the embeddings,
        # but the plan suggests return_predictor=true stores the predictor.
        predictor.set_image(image_data)

        # Store in cache
        object_id = uuid.uuid4().hex
        OBJECT_CACHE.set(object_id, predictor)

        return [
            {
                "type": "ObjectRef",
                "format": "pickle",
                "ref_id": object_id,
                "uri": f"obj://{object_id}",
                "python_class": "segment_anything.predictor.SamPredictor",
                "storage_type": "memory",
                "metadata": {
                    "model": model_type,
                    "device": device,
                },
            }
        ]

    def _load_image(self, artifact: Artifact) -> np.ndarray | Any:
        """Load image data or resolve ObjectRef from cache."""
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
            path = artifact.get("path")
            fmt = artifact.get("format")
            ref_id = artifact.get("ref_id")
            art_type = artifact.get("type")
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)
            fmt = getattr(artifact, "format", None)
            ref_id = getattr(artifact, "ref_id", None)
            art_type = getattr(artifact, "type", None)

        # Resolve ObjectRef from cache
        if (uri and str(uri).startswith("obj://")) or fmt == "pickle" or art_type == "ObjectRef":
            obj = None
            if uri:
                obj = OBJECT_CACHE.get(uri)
            if obj is None and ref_id:
                from bioimage_mcp.registry.dynamic.object_cache import get_by_artifact_id

                obj = get_by_artifact_id(ref_id)

            if obj is not None:
                return obj
            raise ValueError(f"ObjectRef {ref_id or uri} not found in memory cache.")

        # Load BioImageRef / LabelImageRef
        if not uri and not path:
            raise ValueError(f"Artifact missing both URI and path: {artifact}")

        if uri and not path:
            parsed = urlparse(uri)
            if parsed.scheme == "file":
                path = unquote(parsed.path)
                if path.startswith("/") and len(path) > 2 and path[2] == ":":
                    path = path[1:]
            else:
                # Handle other schemes if bioio supports them, or fail
                path = uri

        from bioio import BioImage

        img = BioImage(path)
        try:
            data = img.reader.xarray_data.values
        except (AttributeError, Exception):
            data = img.reader.data

        if hasattr(data, "compute"):
            data = data.compute()

        return data

    def _save_image(
        self,
        array: np.ndarray,
        work_dir: Path,
        axes: str = "YX",
        artifact_type: str = "LabelImageRef",
    ) -> dict:
        """Save array as OME-Zarr and return artifact reference."""
        # Ensure Dtype safety for labels
        if array.dtype == np.int64:
            array = array.astype(np.int32)

        out_path = work_dir / f"output_{uuid.uuid4().hex[:8]}.ome.zarr"

        try:
            from bioio_ome_zarr.writers import OMEZarrWriter

            axes_names = [d.lower() for d in axes]
            type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
            axes_types = [type_map.get(d, "other") for d in axes_names]

            writer = OMEZarrWriter(
                store=str(out_path),
                level_shapes=[array.shape],
                dtype=array.dtype,
                axes_names=axes_names,
                axes_types=axes_types,
            )
            writer.write_full_volume(array)
        except Exception as e:
            logger.warning(f"Failed to write OME-Zarr: {e}. Falling back to TIFF.")
            out_path = out_path.with_suffix(".tif")
            import tifffile

            tifffile.imwrite(out_path, array)

        return {
            "type": artifact_type,
            "format": "OME-Zarr" if out_path.suffix == ".zarr" else "TIFF",
            "uri": out_path.absolute().as_uri(),
            "path": str(out_path.absolute()),
            "metadata": {
                "axes": axes,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "background": 0,
            },
        }

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern based on function name and module path."""
        if "prompt_based_segmentation" in func_name:
            return IOPattern.IMAGE_TO_LABELS
        if "instance_segmentation" in func_name:
            return IOPattern.IMAGE_TO_LABELS

        return IOPattern.GENERIC

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        # Generic hints for SAM-based tools can be added here in the future
        return None
