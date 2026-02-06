"""
Adapter for micro_sam functions.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import os
import pkgutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.errors import BioimageMcpError
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.introspection import Introspector
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

logger = logging.getLogger(__name__)


class HeadlessDisplayRequiredError(BioimageMcpError):
    """Raised when an interactive tool is launched without a display."""

    code = "HEADLESS_DISPLAY_REQUIRED"


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
    "embedding_path",
    "segmentation_result",
}


class MicrosamAdapter(BaseAdapter):
    """Adapter for exposing micro_sam functions dynamically."""

    def __init__(self) -> None:
        self.introspector = Introspector()
        self.warnings: list[str] = []
        self._cache_index: dict[str, dict[str, Any]] = {}

    def _get_cache_key(self, artifact: Artifact, model_type: str) -> str | None:
        """Build deterministic cache key for image + model."""
        if isinstance(artifact, dict):
            uri = artifact.get("uri")
        else:
            uri = getattr(artifact, "uri", None)

        if not uri:
            return None

        return f"microsam_predictor:{uri}:{model_type}"

    def _get_cached_predictor(
        self, artifact: Artifact, model_type: str, force_fresh: bool = False
    ) -> Any | None:
        """Retrieve compatible predictor from cache or return None."""
        key = self._get_cache_key(artifact, model_type)
        if not key:
            return None

        if force_fresh:
            self.warnings.append("MICROSAM_CACHE_RESET")
            OBJECT_CACHE.evict(key)
            self._cache_index.pop(key, None)
            return None

        predictor = OBJECT_CACHE.get(key)
        if predictor is None:
            return None

        # Basic compatibility check
        if not hasattr(predictor, "set_image"):
            self.warnings.append("MICROSAM_CACHE_CORRUPT")
            OBJECT_CACHE.evict(key)
            self._cache_index.pop(key, None)
            return None

        if "MICROSAM_CACHE_HIT" not in self.warnings:
            self.warnings.append("MICROSAM_CACHE_HIT")
        return predictor

    def _check_gui_available(self) -> None:
        """Check if a GUI display is available."""
        if os.environ.get("BIOIMAGE_MCP_FORCE_HEADLESS") == "1":
            raise HeadlessDisplayRequiredError(
                "Interactive annotators require a display. Forced headless mode enabled."
            )

        if sys.platform != "linux":
            return

        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return

        if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
            wsl_runtime = Path("/mnt/wslg/runtime-dir")
            if (wsl_runtime / "wayland-0").exists():
                os.environ.setdefault("XDG_RUNTIME_DIR", str(wsl_runtime))
                os.environ.setdefault("WAYLAND_DISPLAY", "wayland-0")
                return
            if Path("/tmp/.X11-unix/X0").exists():
                os.environ.setdefault("DISPLAY", ":0")
                return

        raise HeadlessDisplayRequiredError(
            "Interactive annotators require a display (DISPLAY or WAYLAND_DISPLAY). "
            "Run in a desktop session or use remote desktop (VNC/Xvfb)."
        )

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
            # Exclude private/test modules
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

                # For micro_sam, we allow re-exports because many key functions
                # are imported from submodules or other packages (like torch_em).
                # But we still want to avoid massive duplication across all modules.
                # Heuristic: only include if the module name matches our mod_name,
                # OR if it's an explicit re-export in an __init__.py.
                is_direct = getattr(obj, "__module__", None) == mod_name
                is_init_reexport = mod_name.endswith(".__init__") or (
                    Path(module.__file__).name == "__init__.py"
                    if hasattr(module, "__file__")
                    else False
                )

                if not (is_direct or is_init_reexport):
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
        self.warnings = []

        # Handle static/manual functions first
        if fn_id == "micro_sam.cache.clear":
            from bioimage_mcp.registry.dynamic.object_cache import clear

            clear()
            self._cache_index = {}
            self.warnings.append("MICROSAM_CACHE_RESET")
            return []

        if fn_id == "micro_sam.compute_embedding":
            return self._execute_compute_embedding(inputs, params)

        if fn_id == "micro_sam.instance_segmentation.automatic_mask_generator":
            return self._execute_amg(inputs, params, work_dir)

        if "sam_annotator" in fn_id:
            entrypoints = {
                "micro_sam.sam_annotator.annotator_2d",
                "micro_sam.sam_annotator.annotator_3d",
                "micro_sam.sam_annotator.annotator_tracking",
                "micro_sam.sam_annotator.image_series_annotator",
            }
            if fn_id in entrypoints:
                return self._execute_interactive(fn_id, inputs, params, work_dir, hints)

            raise RuntimeError(
                f"Function {fn_id} is denylisted for headless execution. "
                "Only main annotator entrypoints are supported for interactive bridge."
            )

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

        kwargs = {}
        param_names = set(inspect.signature(func).parameters.keys())

        # Resolve device from hints or params
        device_pref = params.get("device")
        if device_pref is None and hints:
            device_pref = hints.get("device")
        if device_pref is None:
            device_pref = "auto"

        if "device" in param_names and "device" not in params:
            kwargs["device"] = device_pref

        force_fresh = params.get("force_fresh", False)
        model_type = params.get("model_type", params.get("model", "vit_b"))

        # Prompt coercion: convert lists to numpy arrays for specific SAM parameters
        processed_params = params.copy()
        for p_name in [
            "points",
            "labels",
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
        primary_image_artifact = None
        for name, artifact in self._normalize_inputs(inputs):
            val = self._load_image(artifact)

            if isinstance(val, np.ndarray):
                # Try to extract axes metadata from the primary image
                if isinstance(artifact, dict):
                    input_axes = artifact.get("metadata", {}).get("axes", "YX")
                else:
                    input_axes = getattr(artifact, "metadata", {}) or {}
                    input_axes = input_axes.get("axes", "YX")

                if primary_image_artifact is None:
                    primary_image_artifact = artifact

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
            else:
                # Fallback: if name doesn't match and we don't have this object yet,
                # try to guess based on type.
                if isinstance(val, np.ndarray):
                    if "image" in param_names and "image" not in kwargs:
                        kwargs["image"] = val
                else:
                    if "predictor" in param_names and "predictor" not in kwargs:
                        kwargs["predictor"] = val
                    elif "embedding" in param_names and "embedding" not in kwargs:
                        kwargs["embedding"] = val

        # Handle implicit predictor cache if function needs one and none provided
        if (
            "predictor" in param_names
            and kwargs.get("predictor") is None
            and primary_image_artifact is not None
        ):
            predictor = self._get_cached_predictor(
                primary_image_artifact, model_type, force_fresh=force_fresh
            )
            if predictor is not None:
                kwargs["predictor"] = predictor
            else:
                # Need to load/set it
                # Many SAM functions might not know how to handle just 'image'
                # if they expect 'predictor'.
                # We reuse the logic from AMG/compute_embedding if needed.
                from bioimage_mcp_microsam.device import select_device
                from micro_sam import util

                device = select_device(device_pref)
                predictor = util.get_sam_model(model_type=model_type, device=device)

                # Ensure image is RGB for SAM
                image_data = kwargs.get("image")
                if image_data is None:
                    image_data = self._load_image(primary_image_artifact)

                if image_data.ndim == 2:
                    image_data_rgb = np.stack([image_data] * 3, axis=-1)
                else:
                    image_data_rgb = image_data

                predictor.set_image(image_data_rgb)
                kwargs["predictor"] = predictor

                # Cache it
                key = self._get_cache_key(primary_image_artifact, model_type)
                if key:
                    # We also store it under the deterministic key for image+model lookup
                    OBJECT_CACHE.set(key, predictor)

                    if "MICROSAM_CACHE_HIT" not in self.warnings:
                        self.warnings.append("MICROSAM_CACHE_MISS")

                    import os

                    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
                    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-microsam")
                    object_id = uuid.uuid4().hex
                    obj_uri = f"obj://{session_id}/{env_id}/{object_id}"
                    OBJECT_CACHE.set(obj_uri, predictor)

                    ref = {
                        "type": "ObjectRef",
                        "format": "pickle",
                        "ref_id": object_id,
                        "uri": obj_uri,
                        "python_class": "segment_anything.predictor.SamPredictor",
                        "storage_type": "memory",
                        "metadata": {
                            "model": model_type,
                            "device": device,
                        },
                    }
                    self._cache_index[key] = ref

        # Execute the function
        try:
            # For SAM functions, we prefer all-kwargs call to avoid positional mess
            result = func(**kwargs, **processed_params)
        except Exception as e:
            logger.error(f"Error executing {fn_id}: {e}")
            raise

        # Handle output: return LabelImageRef for arrays, ObjectRef for others
        if isinstance(result, np.ndarray):
            # Segmentation result (Labels)
            # Squeeze extra dimensions to match input axes if possible (Native Dims)
            if result.ndim > len(input_axes):
                # Try to squeeze to match input_axes length
                target_ndim = len(input_axes)
                while result.ndim > target_ndim and 1 in result.shape:
                    result = result.squeeze(axis=result.shape.index(1))

            output_ref = self._save_image(
                result, work_dir, axes=input_axes, artifact_type="LabelImageRef"
            )
            return [output_ref]
        elif result is None:
            return []
        else:
            # Stateful object (Predictor, Embedding, etc.)
            import os

            session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
            env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-microsam")

            object_id = uuid.uuid4().hex
            obj_uri = f"obj://{session_id}/{env_id}/{object_id}"
            OBJECT_CACHE.set(obj_uri, result)

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
        model_type = params.get("model", "vit_b")
        force_fresh = params.get("force_fresh", False)

        # Check cache
        predictor = self._get_cached_predictor(image_artifact, model_type, force_fresh=force_fresh)
        if predictor is not None:
            # We already have it in OBJECT_CACHE, but we need to find its URI/ID
            # Actually, _get_cached_predictor returns the object.
            # We need to return an ObjectRef that points to it.
            # Since we want to return the EXACT same ObjectRef if possible,
            # we should look it up in _cache_index.
            key = self._get_cache_key(image_artifact, model_type)
            cached_meta = self._cache_index.get(key)
            if cached_meta:
                return [cached_meta]

        image_data = self._load_image(image_artifact)

        # Ensure image is RGB-compatible for SAM
        if image_data.ndim == 2:
            image_data = np.stack([image_data] * 3, axis=-1)
        elif image_data.ndim == 3 and image_data.shape[0] in (1, 3):
            # Convert CYX to YXC
            image_data = np.transpose(image_data, (1, 2, 0))
            if image_data.shape[-1] == 1:
                image_data = np.concatenate([image_data] * 3, axis=-1)

        # Resolve device
        from bioimage_mcp_microsam.device import select_device

        device = select_device(params.get("device", "auto"))

        predictor = util.get_sam_model(model_type=model_type, device=device)

        # Compute embedding
        predictor.set_image(image_data)

        # Store in cache
        import os

        session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
        env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-microsam")

        object_id = uuid.uuid4().hex
        obj_uri = f"obj://{session_id}/{env_id}/{object_id}"
        OBJECT_CACHE.set(obj_uri, predictor)

        # Record in adapter-owned cache index for reuse
        key = self._get_cache_key(image_artifact, model_type)
        if key:
            # We also store it under the deterministic key for image+model lookup
            OBJECT_CACHE.set(key, predictor)

            if "MICROSAM_CACHE_HIT" not in self.warnings:
                self.warnings.append("MICROSAM_CACHE_MISS")

            ref = {
                "type": "ObjectRef",
                "format": "pickle",
                "ref_id": object_id,
                "uri": obj_uri,
                "python_class": "segment_anything.predictor.SamPredictor",
                "storage_type": "memory",
                "metadata": {
                    "model": model_type,
                    "device": device,
                },
            }
            self._cache_index[key] = ref
            return [ref]

        return [
            {
                "type": "ObjectRef",
                "format": "pickle",
                "ref_id": object_id,
                "uri": obj_uri,
                "python_class": "segment_anything.predictor.SamPredictor",
                "storage_type": "memory",
                "metadata": {
                    "model": model_type,
                    "device": device,
                },
            }
        ]

    def _execute_amg(
        self, inputs: list[Artifact] | dict[str, Any], params: dict[str, Any], work_dir: Path
    ) -> list[dict]:
        """Manual implementation for automatic mask generation."""
        from micro_sam import util
        from micro_sam.instance_segmentation import (
            AutomaticMaskGenerator,
        )

        normalized = self._normalize_inputs(inputs)
        image_artifact = next(
            (art for name, art in normalized if "image" in name or name == "0"), None
        )
        if image_artifact is None:
            raise ValueError("No input image provided for automatic_mask_generator.")

        model_type = params.get("model_type", "vit_b")
        force_fresh = params.get("force_fresh", False)

        predictor_artifact = next((art for name, art in normalized if "predictor" in name), None)
        predictor = None

        if predictor_artifact:
            predictor = self._load_image(predictor_artifact)
        else:
            # Consult cache if no explicit predictor provided
            predictor = self._get_cached_predictor(
                image_artifact, model_type, force_fresh=force_fresh
            )

        if predictor is None:
            image_data = self._load_image(image_artifact)
            # Ensure RGB
            if image_data.ndim == 2:
                image_data_rgb = np.stack([image_data] * 3, axis=-1)
            else:
                image_data_rgb = image_data

            from bioimage_mcp_microsam.device import select_device

            device = select_device(params.get("device", "auto"))
            predictor = util.get_sam_model(model_type=model_type, device=device)
            predictor.set_image(image_data_rgb)

            # Update cache if possible
            key = self._get_cache_key(image_artifact, model_type)
            if key:
                # We also store it under the deterministic key for image+model lookup
                OBJECT_CACHE.set(key, predictor)

                if "MICROSAM_CACHE_HIT" not in self.warnings:
                    self.warnings.append("MICROSAM_CACHE_MISS")

                import os

                session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
                env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-microsam")
                object_id = uuid.uuid4().hex
                obj_uri = f"obj://{session_id}/{env_id}/{object_id}"
                OBJECT_CACHE.set(obj_uri, predictor)

                ref = {
                    "type": "ObjectRef",
                    "format": "pickle",
                    "ref_id": object_id,
                    "uri": obj_uri,
                    "python_class": "segment_anything.predictor.SamPredictor",
                    "storage_type": "memory",
                    "metadata": {
                        "model": model_type,
                        "device": device,
                    },
                }
                self._cache_index[key] = ref

        image_data = self._load_image(image_artifact)
        input_axes = "YX"
        if isinstance(image_artifact, dict):
            input_axes = image_artifact.get("metadata", {}).get("axes", "YX")

        # Ensure RGB
        if image_data.ndim == 2:
            image_data_rgb = np.stack([image_data] * 3, axis=-1)
        else:
            image_data_rgb = image_data

        points_per_side = params.get("points_per_side", 16)
        amg = AutomaticMaskGenerator(predictor, points_per_side=points_per_side)

        # If image is 3D but we want 2D AMG, we might need to specify i=0 or similar.
        # However, for RGB (H, W, 3), ndim is 3.
        # Micro-sam might need to know if it's RGB or volumetric.
        # We try to initialize. If it fails with "3D" error, we might need to adjust.
        try:
            amg.initialize(image_data_rgb)
        except (RuntimeError, ValueError) as e:
            if "3D" in str(e) and image_data_rgb.ndim == 3:
                # Try with i=0 if it's treated as volumetric
                amg.initialize(image_data_rgb, i=0)
            else:
                raise

        labels = amg.generate()

        # Squeeze extra dimensions to match input axes if possible
        if labels.ndim > len(input_axes):
            target_ndim = len(input_axes)
            while labels.ndim > target_ndim and 1 in labels.shape:
                labels = labels.squeeze(axis=labels.shape.index(1))

        output_ref = self._save_image(
            labels, work_dir, axes=input_axes, artifact_type="LabelImageRef"
        )
        return [output_ref]

    def _execute_interactive(
        self,
        fn_id: str,
        inputs: list[Artifact] | dict[str, Any],
        params: dict[str, Any],
        work_dir: Path | None,
        hints: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Execute micro_sam interactive annotator."""
        self._check_gui_available()

        try:
            import napari
            from micro_sam import sam_annotator
        except ImportError as e:
            raise RuntimeError(
                f"Interactive dependencies (napari, micro_sam) not found: {e}"
            ) from e

        if work_dir is None:
            work_dir = Path(tempfile.gettempdir()) / "microsam"
        work_dir.mkdir(parents=True, exist_ok=True)

        normalized = self._normalize_inputs(inputs)
        image_data: np.ndarray | None = None
        image_artifact: Artifact | None = None
        embedding_value: Any = None
        segmentation_value: Any = None

        force_fresh = params.get("force_fresh", False)
        model_type = params.get("model_type", params.get("model", "vit_b"))

        for name, artifact in normalized:
            # Consult cache for embedding/predictor if not explicitly provided
            if (
                name in {"embedding_path", "predictor", "embedding"}
                and embedding_value is None
                and image_artifact is not None
            ):
                embedding_value = self._get_cached_predictor(
                    image_artifact, model_type, force_fresh=force_fresh
                )

            value = self._load_image(artifact)
            if name == "image" or (image_data is None and isinstance(value, np.ndarray)):
                image_data = np.asarray(value)
                image_artifact = artifact
                continue

            if name in {"embedding_path", "predictor", "embedding"} and embedding_value is None:
                embedding_value = value
                continue

            if (
                name in {"segmentation_result", "labels", "label_image"}
                and segmentation_value is None
            ):
                segmentation_value = value

        if image_data is None:
            raise ValueError("Interactive annotator requires an image input.")

        # If embedding still None, check cache again now that we definitely have image_artifact
        if embedding_value is None and image_artifact is not None:
            embedding_value = self._get_cached_predictor(
                image_artifact, model_type, force_fresh=force_fresh
            )
            # If still None, we don't automatically compute it for interactive yet,
            # as napari widget handles it or compute_embedding should have been called.
            # But the requirement says "warm-start from existing state when compatible".
            if embedding_value is None:
                if "MICROSAM_CACHE_HIT" not in self.warnings:
                    self.warnings.append("MICROSAM_CACHE_MISS")
        elif embedding_value is not None:
            # If we got it from cache, _get_cached_predictor already appended HIT
            pass

        input_axes = "YX"
        if isinstance(image_artifact, dict):
            input_axes = image_artifact.get("metadata", {}).get("axes", "YX")
        elif image_artifact is not None:
            metadata = getattr(image_artifact, "metadata", {}) or {}
            if isinstance(metadata, dict):
                input_axes = metadata.get("axes", "YX")

        func_name = fn_id.split(".")[-1]
        try:
            annotator_fn = getattr(sam_annotator, func_name)
        except AttributeError as e:
            raise RuntimeError(f"Annotator function not found: {fn_id}") from e

        signature = inspect.signature(annotator_fn)
        accepts_var_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
        )

        def accepts(name: str) -> bool:
            return accepts_var_kwargs or name in signature.parameters

        device_pref = params.get("device")
        if device_pref is None and hints:
            device_pref = hints.get("device")
        if device_pref is None:
            device_pref = "auto"

        call_kwargs: dict[str, Any] = {}

        if accepts("image"):
            call_kwargs["image"] = image_data
        elif accepts("raw"):
            call_kwargs["raw"] = image_data
        else:
            call_kwargs["image"] = image_data

        if embedding_value is not None:
            if accepts("embedding_path"):
                call_kwargs["embedding_path"] = embedding_value
            elif accepts("predictor"):
                call_kwargs["predictor"] = embedding_value
            elif accepts("embedding"):
                call_kwargs["embedding"] = embedding_value

        if segmentation_value is not None:
            if accepts("segmentation_result"):
                call_kwargs["segmentation_result"] = segmentation_value
            elif accepts("labels"):
                call_kwargs["labels"] = segmentation_value
            elif accepts("label_image"):
                call_kwargs["label_image"] = segmentation_value

        if accepts("device"):
            call_kwargs["device"] = device_pref

        if accepts("return_viewer"):
            call_kwargs["return_viewer"] = True

        for key, value in params.items():
            if key in ARTIFACT_INPUT_PARAMS:
                continue
            if accepts(key) and key not in call_kwargs:
                call_kwargs[key] = value

        viewer = annotator_fn(**call_kwargs)
        if viewer is None:
            self.warnings.append("MICROSAM_NO_CHANGES")
            return []

        captured_labels: np.ndarray | None = None

        def capture_layer_data(layer: Any) -> None:
            nonlocal captured_labels
            try:
                data = np.asarray(getattr(layer, "data", None))
            except RuntimeError:
                return
            if data.size == 0 or not np.any(data):
                return
            captured_labels = np.array(data)

        def on_layer_removed(event: Any) -> None:
            layer = getattr(event, "value", None)
            if getattr(layer, "name", None) == "committed_objects":
                capture_layer_data(layer)

        layers = None
        try:
            layers = getattr(viewer, "layers", None)
        except RuntimeError:
            layers = None

        if layers is not None:
            if hasattr(layers, "events") and hasattr(layers.events, "removed"):
                layers.events.removed.connect(on_layer_removed)
            if hasattr(layers, "get"):
                existing = layers.get("committed_objects")
                if existing is not None:
                    capture_layer_data(existing)

        napari.run()

        try:
            layers = getattr(viewer, "layers", None)
        except RuntimeError as e:
            if "has been deleted" in str(e):
                logger.warning("Napari viewer was deleted before layer extraction: %s", e)
                self.warnings.append("MICROSAM_NO_CHANGES")
                return []
            raise

        committed_layer = None
        if layers is not None and hasattr(layers, "get"):
            committed_layer = layers.get("committed_objects")
        if committed_layer is None and isinstance(layers, dict):
            committed_layer = layers.get("committed_objects")
        if committed_layer is None and layers is not None:
            for layer in layers:
                if getattr(layer, "name", None) == "committed_objects":
                    committed_layer = layer
                    break

        labels: np.ndarray | None = None
        if committed_layer is not None:
            labels = np.asarray(getattr(committed_layer, "data", None))
        elif captured_labels is not None:
            labels = captured_labels

        if labels is None:
            self.warnings.append("MICROSAM_NO_CHANGES")
            return []

        if labels.size == 0 or not np.any(labels):
            self.warnings.append("MICROSAM_NO_CHANGES")
            return []

        if segmentation_value is not None:
            try:
                existing = np.asarray(segmentation_value)
                if existing.shape == labels.shape and np.array_equal(existing, labels):
                    self.warnings.append("MICROSAM_NO_CHANGES")
                    return []
            except Exception:
                pass

        output_ref = self._save_image(
            labels,
            work_dir,
            axes=input_axes,
            artifact_type="LabelImageRef",
        )
        return [output_ref]

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
            if "segment" in func_name:
                return IOPattern.SAM_PROMPT
        if "instance_segmentation" in func_name:
            if "segment" in func_name or "watershed" in func_name or "automatic" in func_name:
                return IOPattern.SAM_AMG
        if "sam_annotator" in func_name:
            # Entrypoints for interactive annotators
            entrypoints = {
                "annotator_2d",
                "annotator_3d",
                "annotator_tracking",
                "image_series_annotator",
            }
            if any(ep in func_name for ep in entrypoints):
                return IOPattern.SAM_ANNOTATOR

        return IOPattern.DYNAMIC

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        # Generic hints for SAM-based tools can be added here in the future
        return None
