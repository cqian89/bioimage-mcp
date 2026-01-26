from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import pandas as pd

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema

# In-memory object cache for pandas DataFrames and GroupBy objects
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE
from bioimage_mcp.registry.dynamic.pandas_adapter import ObjectNotFoundError


class PandasAdapterForRegistry(BaseAdapter):
    """Adapter for pandas operations that satisfies the BaseAdapter protocol."""

    def __init__(self) -> None:
        from bioimage_mcp.registry.dynamic.pandas_adapter import PandasAdapter
        from bioimage_mcp.registry.dynamic.pandas_allowlists import PANDAS_DATAFRAME_METHODS

        self.core = PandasAdapter(allowlist=PANDAS_DATAFRAME_METHODS)

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Dynamically discover pandas functions from the allowlists."""
        from bioimage_mcp.registry.dynamic.pandas_allowlists import (
            PANDAS_DATAFRAME_CLASS,
            PANDAS_DATAFRAME_METHODS,
            PANDAS_GROUPBY_METHODS,
            PANDAS_TOPLEVEL_FUNCTIONS,
            PandasSignatureType,
        )

        discovery: list[FunctionMetadata] = []

        # 1. Constructor: base.pandas.DataFrame
        for name, info in PANDAS_DATAFRAME_CLASS.items():
            params = self._convert_params(info.get("params", {}))
            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="pandas",
                    qualified_name=f"pandas.{name}",
                    fn_id=f"base.pandas.{name}",
                    source_adapter="pandas",
                    description=info.get("summary", ""),
                    parameters=params,
                    tags=info.get("tags", []),
                    io_pattern=IOPattern.CONSTRUCTOR,
                )
            )

        # 2. DataFrame methods: base.pandas.DataFrame.<name>
        for name, info in PANDAS_DATAFRAME_METHODS.items():
            params = self._convert_params(info.get("params", {}))

            # Decide IO pattern
            if info.get("signature_type") == PandasSignatureType.GROUPBY:
                io_pattern = IOPattern.OBJECTREF_CHAIN  # df -> groupby obj
            elif info.get("returns") == "TableRef":
                io_pattern = (
                    IOPattern.OBJECT_TO_IMAGE
                )  # Actually OBJECT_TO_TABLE, but using what's available
            else:
                io_pattern = IOPattern.OBJECTREF_CHAIN

            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="pandas.DataFrame",
                    qualified_name=f"pandas.DataFrame.{name}",
                    fn_id=f"base.pandas.DataFrame.{name}",
                    source_adapter="pandas",
                    description=info.get("summary", ""),
                    parameters=params,
                    tags=info.get("tags", []),
                    io_pattern=io_pattern,
                )
            )

        # 3. GroupBy methods: base.pandas.GroupBy.<name>
        for name, info in PANDAS_GROUPBY_METHODS.items():
            params = self._convert_params(info.get("params", {}))
            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="pandas.core.groupby.DataFrameGroupBy",
                    qualified_name=f"pandas.core.groupby.DataFrameGroupBy.{name}",
                    fn_id=f"base.pandas.GroupBy.{name}",
                    source_adapter="pandas",
                    description=info.get("summary", ""),
                    parameters=params,
                    tags=info.get("tags", ["groupby", "pandas"]),
                    io_pattern=IOPattern.OBJECTREF_CHAIN,
                )
            )

        # 4. Top-level functions: base.pandas.<name>
        for name, info in PANDAS_TOPLEVEL_FUNCTIONS.items():
            params = self._convert_params(info.get("params", {}))
            discovery.append(
                FunctionMetadata(
                    name=name,
                    module="pandas",
                    qualified_name=f"pandas.{name}",
                    fn_id=f"base.pandas.{name}",
                    source_adapter="pandas",
                    description=info.get("summary", ""),
                    parameters=params,
                    tags=info.get("tags", []),
                    io_pattern=IOPattern.MULTI_TABLE_INPUT
                    if info.get("signature_type") == PandasSignatureType.MULTI_INPUT
                    else IOPattern.IMAGE_TO_IMAGE,
                )
            )

        return discovery

    def _convert_params(self, params_info: dict[str, Any]) -> dict[str, ParameterSchema]:
        params = {}
        for p_name, p_info in params_info.items():
            if isinstance(p_info, str):
                params[p_name] = ParameterSchema(name=p_name, type=p_info)
            elif isinstance(p_info, dict):
                params[p_name] = ParameterSchema(name=p_name, **p_info)
        return params

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        return IOPattern.OBJECTREF_CHAIN

    def _normalize_inputs(self, inputs: list[Artifact]) -> list[tuple[str, Artifact]]:
        """Normalize inputs to (name, artifact) tuples."""
        normalized: list[tuple[str, Artifact]] = []
        for idx, item in enumerate(inputs):
            if isinstance(item, tuple) and len(item) == 2:
                name, artifact = item
            else:
                name = "tables" if idx == 0 else f"input_{idx}"
                artifact = item
            normalized.append((str(name), artifact))
        return normalized

    def _load_table(self, artifact: Artifact) -> pd.DataFrame:
        """Load DataFrame from artifact (TableRef or ObjectRef or URI string)."""
        if isinstance(artifact, str):
            uri = artifact
            path = None
        elif isinstance(artifact, dict):
            uri = artifact.get("uri")
            path = artifact.get("path")
        else:
            uri = getattr(artifact, "uri", None)
            path = getattr(artifact, "path", None)

        if uri and uri.startswith("obj://"):
            if uri not in OBJECT_CACHE:
                raise ObjectNotFoundError(
                    f"ObjectRef with URI '{uri}' not found in cache",
                    details={
                        "hint": (
                            "The object may have been evicted. "
                            "Re-run the operation that created it."
                        )
                    },
                )
            return OBJECT_CACHE[uri]

        if not path and uri:
            parsed = urlparse(str(uri))
            path = unquote(parsed.path)
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

        if not path:
            raise ValueError(f"Artifact missing URI or path: {artifact}")

        # Support Parquet (default for TableRef) and CSV
        path_obj = Path(path)
        if path_obj.suffix == ".parquet":
            return pd.read_parquet(path)
        elif path_obj.suffix == ".csv":
            return pd.read_csv(path)
        else:
            # Try parquet first, then csv
            try:
                return pd.read_parquet(path)
            except Exception:
                return pd.read_csv(path)

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute pandas function."""
        # Normalize inputs - they may come as (name, value) tuples from dispatch
        normalized_inputs = []
        for inp in inputs:
            if isinstance(inp, tuple) and len(inp) == 2:
                normalized_inputs.append(inp[1])  # Extract value from (name, value) tuple
            else:
                normalized_inputs.append(inp)
        inputs = normalized_inputs

        # Handle both cases: adapter may be called directly with "base.pandas." prefix
        # or via entrypoint which strips "base." first
        if fn_id.startswith("base."):
            fn_id = fn_id[5:]  # Strip "base." prefix

        if not fn_id.startswith("pandas."):
            raise ValueError(f"Unsupported pandas function ID: {fn_id}")

        if fn_id == "pandas.DataFrame":
            return self._execute_constructor(inputs, params)

        if fn_id in ["pandas.DataFrame.to_table", "pandas.DataFrame.to_tableref"]:
            return self._execute_to_table(inputs, params, work_dir)

        if fn_id.startswith("pandas.DataFrame."):
            return self._execute_dataframe_method(fn_id, inputs, params, work_dir)

        if fn_id.startswith("pandas.GroupBy."):
            return self._execute_groupby_method(fn_id, inputs, params, work_dir)

        if fn_id.startswith("pandas."):
            return self._execute_toplevel(fn_id, inputs, params, work_dir)

        raise ValueError(f"Unknown pandas function ID: {fn_id}")

    def _execute_constructor(self, inputs: list[Artifact], params: dict[str, Any]) -> list[dict]:
        if not inputs:
            raise ValueError("No input artifact provided for DataFrame constructor")

        df = self._load_table(inputs[0])
        artifact_id = str(uuid.uuid4())
        uri = f"obj://default/pandas/{artifact_id}"
        OBJECT_CACHE[uri] = df

        return [
            {
                "ref_id": artifact_id,
                "type": "ObjectRef",
                "python_class": "pandas.DataFrame",
                "uri": uri,
                "storage_type": "memory",
                "metadata": {
                    "shape": list(df.shape),
                    "columns": list(df.columns),
                },
            }
        ]

    def _execute_dataframe_method(
        self, fn_id: str, inputs: list[Artifact], params: dict[str, Any], work_dir: Path | None
    ) -> list[dict]:
        method_name = fn_id.split(".")[-1]
        if not inputs:
            raise ValueError(f"No input artifact provided for {fn_id}")

        artifact = inputs[0]
        if isinstance(artifact, dict):
            ref_id = artifact.get("ref_id") or artifact.get("uri")
        else:
            ref_id = getattr(artifact, "ref_id", None) or getattr(artifact, "uri", None)

        df = self._load_table(artifact)
        result = self.core.execute(method_name, df, ref_id=ref_id, **params)

        return self._handle_result(result, method_name, work_dir)

    def _execute_groupby_method(
        self, fn_id: str, inputs: list[Artifact], params: dict[str, Any], work_dir: Path | None
    ) -> list[dict]:
        method_name = fn_id.split(".")[-1]
        if not inputs:
            raise ValueError(f"No input artifact provided for {fn_id}")

        # Load the GroupBy object from cache
        uri = (
            inputs[0].get("uri") if isinstance(inputs[0], dict) else getattr(inputs[0], "uri", None)
        )
        if not uri or uri not in OBJECT_CACHE:
            raise ObjectNotFoundError(
                f"ObjectRef with URI '{uri}' not found in cache",
                details={
                    "hint": (
                        "The object may have been evicted. Re-run the operation that created it."
                    )
                },
            )

        groupby_obj = OBJECT_CACHE[uri]

        if not hasattr(groupby_obj, method_name):
            raise ValueError(f"GroupBy object does not have method {method_name}")

        method = getattr(groupby_obj, method_name)
        result = method(**params)

        return self._handle_result(result, method_name, work_dir)

    def _execute_toplevel(
        self, fn_id: str, inputs: list[Artifact], params: dict[str, Any], work_dir: Path | None
    ) -> list[dict]:
        method_name = fn_id.split(".")[-1]

        # Normalize inputs to handle both direct and dispatch patterns
        normalized = self._normalize_inputs(inputs)

        # Collect all DataFrames, handling nested lists
        dfs = []
        for _name, art in normalized:
            if isinstance(art, list):
                # Handle inputs=[("tables", [ref1, ref2])] from dynamic_dispatch
                for item in art:
                    dfs.append(self._load_table(item))
            else:
                # Handle inputs=[("table_0", ref1), ("table_1", ref2)]
                dfs.append(self._load_table(art))

        if not dfs:
            raise ValueError(f"No input DataFrames found for {fn_id}")

        if method_name == "concat":
            result = self.core.concat(dfs, **params)
        elif method_name == "merge":
            if len(dfs) < 2:
                raise ValueError("merge requires at least two input DataFrames")
            result = self.core.merge(dfs[0], dfs[1], **params)
        else:
            func = getattr(pd, method_name)
            result = func(*dfs, **params)

        return self._handle_result(result, method_name, work_dir)

    def _execute_to_table(
        self, inputs: list[Artifact], params: dict[str, Any], work_dir: Path | None
    ) -> list[dict]:
        if not inputs:
            raise ValueError("No input artifact provided for to_table")

        df = self._load_table(inputs[0])
        fmt = params.get("format", "parquet")
        return self._save_table(df, "exported", work_dir, format=fmt)

    def _handle_result(self, result: Any, method_name: str, work_dir: Path | None) -> list[dict]:
        if isinstance(result, (pd.DataFrame, pd.Series)):
            if isinstance(result, pd.Series):
                result = result.to_frame()

            artifact_id = str(uuid.uuid4())
            uri = f"obj://default/pandas/{artifact_id}"
            OBJECT_CACHE[uri] = result

            return [
                {
                    "ref_id": artifact_id,
                    "type": "ObjectRef",
                    "python_class": "pandas.DataFrame",
                    "uri": uri,
                    "storage_type": "memory",
                    "metadata": {
                        "shape": list(result.shape),
                        "columns": list(result.columns),
                    },
                }
            ]
        elif "groupby" in str(type(result)).lower():
            artifact_id = str(uuid.uuid4())
            uri = f"obj://default/pandas/groupby-{artifact_id}"
            OBJECT_CACHE[uri] = result

            # Extract metadata for GroupByRef
            # Use result.keys (stable API) instead of deprecated result.grouper.names
            grouped_by = []
            if hasattr(result, "keys"):
                keys = result.keys
                if isinstance(keys, list):
                    grouped_by = [str(k) for k in keys if k is not None]
                elif keys is not None:
                    grouped_by = [str(keys)]

            groups_count = 0
            if hasattr(result, "ngroups"):
                groups_count = result.ngroups

            return [
                {
                    "ref_id": artifact_id,
                    "type": "GroupByRef",
                    "python_class": "pandas.core.groupby.DataFrameGroupBy",
                    "uri": uri,
                    "storage_type": "memory",
                    "metadata": {
                        "grouped_by": grouped_by,
                        "groups_count": groups_count,
                    },
                }
            ]
        else:
            # Scalar or other result - wrap in DataFrame
            df_result = pd.DataFrame([{"result": result}])
            return self._handle_result(df_result, method_name, work_dir)

    def _save_table(
        self, df: pd.DataFrame, name: str, work_dir: Path | None, format: str = "parquet"
    ) -> list[dict]:
        if work_dir is None:
            work_dir = Path(tempfile.gettempdir())

        work_dir.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            out_path = work_dir / f"{name}.csv"
            include_index = not isinstance(df.index, pd.RangeIndex) or df.index.name is not None
            df.to_csv(out_path, index=include_index)
        else:
            out_path = work_dir / f"{name}.parquet"
            df.to_parquet(out_path)

        return [
            {
                "type": "TableRef",
                "format": format,
                "uri": out_path.absolute().as_uri(),
                "path": str(out_path.absolute()),
                "metadata": {
                    "shape": list(df.shape),
                    "columns": list(df.columns),
                },
            }
        ]

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        return None
