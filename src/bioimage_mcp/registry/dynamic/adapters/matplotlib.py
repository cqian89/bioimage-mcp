from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.adapters.matplotlib_allowlists import (
    MATPLOTLIB_AXES_ALLOWLIST,
    MATPLOTLIB_DENYLIST,
    MATPLOTLIB_FIGURE_ALLOWLIST,
    MATPLOTLIB_PATCHES_ALLOWLIST,
    MATPLOTLIB_PYPLOT_ALLOWLIST,
)
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement
    from bioimage_mcp.artifacts.base import Artifact
    from bioimage_mcp.artifacts.memory import MemoryArtifactStore


class SessionObjectNotFoundError(ValueError):
    """Raised when obj:// reference is not registered to active session."""

    pass


def _validate_single_ref(
    uri: str,
    ref_id: str | None,
    session_id: str,
    memory_store: MemoryArtifactStore | None,
) -> None:
    """Validate a single obj:// reference against the active session."""
    from bioimage_mcp.artifacts.memory import parse_mem_uri

    if not uri.startswith("obj://"):
        return

    if not ref_id:
        raise SessionObjectNotFoundError(
            f"Object with URI '{uri}' is missing ref_id - cannot validate ownership."
        )

    # 1. Check if registered in memory_store
    if memory_store:
        if not memory_store.exists(ref_id):
            raise SessionObjectNotFoundError(
                f"Object reference '{ref_id}' (URI: {uri}) is not "
                f"registered to session '{session_id}'. "
                "The object may have been evicted, the session may have "
                "expired, or the reference belongs to a different session. "
                "Please recreate the object in this session."
            )

        # 2. Verify session matches by parsing the stored URI
        stored_artifact = memory_store.get(ref_id)
        if stored_artifact:
            stored_session, _, _ = parse_mem_uri(stored_artifact.uri)
            if stored_session != session_id:
                raise SessionObjectNotFoundError(
                    f"Object reference '{ref_id}' (URI: {uri}) is registered "
                    f"to a different session ('{stored_session}'), "
                    f"not the active session '{session_id}'."
                )
    else:
        raise SessionObjectNotFoundError(
            f"Cannot validate object reference '{ref_id}' - memory store not available. "
            f"Session isolation cannot be enforced."
        )


def _validate_params_refs(
    params: dict[str, Any],
    session_id: str,
    memory_store: MemoryArtifactStore | None,
) -> None:
    """Recursively scan params for obj:// references and validate them."""
    for val in params.values():
        if isinstance(val, dict):
            uri = val.get("uri", "")
            if isinstance(uri, str) and uri.startswith("obj://"):
                ref_id = val.get("ref_id")
                # Apply same validation logic as inputs
                _validate_single_ref(uri, ref_id, session_id, memory_store)
            else:
                # Recurse into nested dicts
                _validate_params_refs(val, session_id, memory_store)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    # Check if it's an object ref itself or contains them
                    uri = item.get("uri", "")
                    if isinstance(uri, str) and uri.startswith("obj://"):
                        _validate_single_ref(uri, item.get("ref_id"), session_id, memory_store)
                    else:
                        _validate_params_refs(item, session_id, memory_store)


def _validate_input_ownership(
    inputs: list[Artifact],
    params: dict[str, Any],
    session_id: str,
    memory_store: MemoryArtifactStore | None,
) -> None:
    """Validate that all obj:// references belong to the active session.

    Checks both inputs list and params dict for obj:// URIs.
    """
    for item in inputs:
        # Artifact can be a dict or an object
        if isinstance(item, dict):
            uri = item.get("uri")
            ref_id = item.get("ref_id")
        else:
            uri = getattr(item, "uri", None)
            ref_id = getattr(item, "ref_id", None)

        if uri and isinstance(uri, str) and uri.startswith("obj://"):
            _validate_single_ref(uri, ref_id, session_id, memory_store)

    # Recursively check params for obj:// references
    _validate_params_refs(params, session_id, memory_store)


PATH_PARAM_NAMES = {"fname", "filename", "path", "fpath", "savefig", "outputfile"}
FILE_IO_FUNCTIONS = {"imread", "imsave", "savefig"}


def _looks_like_path(val: Any) -> bool:
    """Heuristically detect if a value looks like a filesystem path."""
    if not isinstance(val, str):
        return False

    # Exclude URIs and URLs
    if any(
        val.startswith(scheme) for scheme in ("http://", "https://", "obj://", "mem://", "file://")
    ):
        return False

    # Check for path anchors (absolute or relative path starts)
    path_anchors = ("/", "\\", "./", ".\\", "../", "..\\", "~")
    if any(val.startswith(anchor) for anchor in path_anchors):
        return True

    # Check Windows drive letters
    if len(val) >= 2 and val[1] == ":" and val[0].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return True

    # Check common file extensions (case insensitive)
    extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".pdf",
        ".svg",
        ".gif",
        ".bmp",
    )
    if any(val.lower().endswith(ext) for ext in extensions):
        return True

    return False


def validate_path_params(
    fn_id: str,
    params: dict[str, Any],
    fs_allowlist_read: list[Path] | None,
    fs_allowlist_write: list[Path] | None,
    method_name: str,
) -> None:
    """Check if any param value looks like a path and validate against allowlist."""
    is_write = method_name in {"imsave", "savefig"}

    for key, val in params.items():
        # Check if param name or value looks like a path
        is_path_param = key.lower() in PATH_PARAM_NAMES or _looks_like_path(val)

        if is_path_param and isinstance(val, str):
            path_obj = Path(val).expanduser().resolve()
            allowlist = fs_allowlist_write if is_write else fs_allowlist_read

            if allowlist is None:
                # If no allowlist is provided, we can't validate, but the constitution says
                # file access MUST be explicit. If we're doing a file operation,
                # we should probably fail if no allowlist is provided.
                # However, for plot(x, y), we don't want to fail.
                # Only fail for explicit FILE_IO_FUNCTIONS or if we're sure it's a path.
                if method_name in FILE_IO_FUNCTIONS:
                    raise ValueError(
                        f"Function {fn_id} requires a path but no "
                        "filesystem allowlist is configured."
                    )
                continue

            # Check against allowlist
            allowed = False
            for allowed_path in allowlist:
                try:
                    resolved_allowed = allowed_path.resolve()
                    path_obj.relative_to(resolved_allowed)
                    allowed = True
                    break
                except (ValueError, RuntimeError):
                    continue

            if not allowed:
                mode = "write" if is_write else "read"
                raise ValueError(
                    f"Path '{val}' is not allowed for {mode} (not in allowed {mode} paths). "
                    f"Function: {fn_id}, Parameter: {key}"
                )


class MatplotlibAdapter(BaseAdapter):
    """Adapter for Matplotlib that satisfies the BaseAdapter protocol."""

    def __init__(self) -> None:
        """Initialize the adapter and enforce the Agg backend."""
        try:
            import matplotlib

            matplotlib.use("Agg")
        except ImportError:
            # Matplotlib might not be available in the core server environment
            # during discovery, which is fine as long as we don't call it.
            pass

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover matplotlib functions from the allowlists."""
        discovery: list[FunctionMetadata] = []

        # Modules requested in config
        requested_modules = module_config.get("modules", [])

        allowlists = [
            (
                "matplotlib.pyplot",
                "matplotlib.pyplot",
                "base.matplotlib.pyplot",
                MATPLOTLIB_PYPLOT_ALLOWLIST,
            ),
            (
                "matplotlib.figure",
                "matplotlib.figure.Figure",
                "base.matplotlib.Figure",
                MATPLOTLIB_FIGURE_ALLOWLIST,
            ),
            (
                "matplotlib.axes",
                "matplotlib.axes.Axes",
                "base.matplotlib.Axes",
                MATPLOTLIB_AXES_ALLOWLIST,
            ),
            (
                "matplotlib.patches",
                "matplotlib.patches",
                "base.matplotlib.patches",
                MATPLOTLIB_PATCHES_ALLOWLIST,
            ),
        ]

        for mod_name, qual_prefix, id_prefix, allowlist in allowlists:
            if not requested_modules or mod_name in requested_modules:
                for name, info in allowlist.items():
                    # Parse parameters
                    params = {}
                    if "params" in info:
                        for p_name, p_info in info["params"].items():
                            params[p_name] = ParameterSchema(
                                name=p_name,
                                type=p_info.get("type", "string"),
                                description=p_info.get("description", ""),
                                default=p_info.get("default"),
                                required=p_info.get("required", False),
                                items=p_info.get("items"),
                            )

                    # Map io_pattern
                    io_pattern_str = info.get("io_pattern", "IMAGE_TO_IMAGE")
                    try:
                        io_pattern = IOPattern[io_pattern_str]
                    except KeyError:
                        io_pattern = IOPattern.IMAGE_TO_IMAGE

                    discovery.append(
                        FunctionMetadata(
                            name=name,
                            module=mod_name,
                            qualified_name=f"{qual_prefix}.{name}",
                            fn_id=f"{id_prefix}.{name}",
                            source_adapter="matplotlib",
                            description=info.get("summary", ""),
                            parameters=params,
                            tags=["visualization", "matplotlib"],
                            io_pattern=io_pattern,
                        )
                    )

        return discovery

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Any = None,
        fs_allowlist_read: list[Path] | None = None,
        fs_allowlist_write: list[Path] | None = None,
        session_id: str | None = None,
        env_id: str = "base",
        memory_store: MemoryArtifactStore | None = None,
    ) -> list[dict]:
        """Execute a matplotlib function.

        Dispatches to implementation in bioimage_mcp_base.ops.matplotlib_ops.
        """
        method_name = fn_id.split(".")[-1]

        # R2.4: Session ownership validation
        if session_id:
            _validate_input_ownership(inputs, params, session_id, memory_store)

        # R1.2: Path validation guardrails
        validate_path_params(fn_id, params, fs_allowlist_read, fs_allowlist_write, method_name)

        # Safety check: Block interactive methods
        if method_name in MATPLOTLIB_DENYLIST:
            raise ValueError(f"Function {fn_id} is blocked for safety (interactive GUI method).")

        # Check if it's in any allowlist
        is_allowed = (
            method_name in MATPLOTLIB_PYPLOT_ALLOWLIST
            or method_name in MATPLOTLIB_FIGURE_ALLOWLIST
            or method_name in MATPLOTLIB_AXES_ALLOWLIST
            or method_name in MATPLOTLIB_PATCHES_ALLOWLIST
        )

        if not is_allowed:
            raise ValueError(f"Function {fn_id} is unknown or not allowed.")

        # Deferred import to avoid heavy dependencies in core server
        from bioimage_mcp_base.ops import matplotlib_ops

        # Normalize inputs for dispatch
        normalized_inputs = self._normalize_inputs(inputs)

        # 1. Specific High-Level Dispatches (require custom logic)
        eff_session_id = session_id or "default"

        if fn_id.endswith("matplotlib.pyplot.subplots"):
            return matplotlib_ops.subplots(session_id=eff_session_id, env_id=env_id, **params)
        if fn_id.endswith("matplotlib.pyplot.figure"):
            return matplotlib_ops.figure(session_id=eff_session_id, env_id=env_id, **params)
        if fn_id.endswith("matplotlib.Axes.imshow"):
            return matplotlib_ops.imshow(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.hist"):
            return matplotlib_ops.hist(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.boxplot"):
            return matplotlib_ops.boxplot(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.violinplot"):
            return matplotlib_ops.violinplot(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.plot"):
            return matplotlib_ops.plot(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.scatter"):
            return matplotlib_ops.scatter(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.add_patch"):
            return matplotlib_ops.add_patch(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Figure.savefig"):
            return matplotlib_ops.savefig(
                normalized_inputs, params, work_dir, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.pyplot.imsave"):
            return matplotlib_ops.imsave(
                normalized_inputs, params, work_dir, session_id=eff_session_id, env_id=env_id
            )
        if fn_id.endswith("matplotlib.Axes.colorbar"):
            return matplotlib_ops.colorbar(
                normalized_inputs, params, session_id=eff_session_id, env_id=env_id
            )

        # 2. Generic Category Dispatches
        if "matplotlib.pyplot" in fn_id:
            return matplotlib_ops.pyplot_op(
                params, method_name, session_id=eff_session_id, env_id=env_id
            )

        if "matplotlib.Figure" in fn_id:
            return matplotlib_ops.generic_op(
                normalized_inputs, params, method_name, session_id=eff_session_id, env_id=env_id
            )

        if "matplotlib.Axes" in fn_id:
            return matplotlib_ops.generic_op(
                normalized_inputs, params, method_name, session_id=eff_session_id, env_id=env_id
            )

        if "matplotlib.patches" in fn_id:
            return matplotlib_ops.patch_op(
                params, method_name, session_id=eff_session_id, env_id=env_id
            )

        return []

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[tuple[str, Artifact]]:
        """Normalize inputs to (name, artifact) tuples."""
        normalized: list[tuple[str, Artifact]] = []
        for idx, item in enumerate(inputs):
            if isinstance(item, tuple) and len(item) == 2:
                name, artifact = item
            else:
                # Heuristic for default names if not provided
                if idx == 0:
                    name = "axes" if "Axes" in str(item) else "figure"
                else:
                    name = f"input_{idx}"
                artifact = item
            normalized.append((str(name), artifact))
        return normalized

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern from function signature."""
        return IOPattern.IMAGE_TO_IMAGE

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints for agent guidance."""
        return None
