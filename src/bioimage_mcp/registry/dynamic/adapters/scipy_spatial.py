from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from bioimage_mcp.registry.dynamic.adapters.scipy_stats import ScipyStatsAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

if TYPE_CHECKING:
    from bioimage_mcp.api.schemas import DimensionRequirement

logger = logging.getLogger(__name__)


class ScipySpatialAdapter(ScipyStatsAdapter):
    """Adapter for scipy.spatial functions."""

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        modules = module_config.get("modules", [])
        if "scipy.spatial" not in modules and "scipy.spatial.distance" not in modules:
            return super().discover(module_config)

        results = []

        # 1. cdist
        results.append(
            FunctionMetadata(
                name="cdist",
                module="scipy.spatial.distance",
                qualified_name="scipy.spatial.distance.cdist",
                fn_id="scipy.spatial.distance.cdist",
                source_adapter="scipy_spatial",
                description="Compute distance between each pair of the two collections of inputs.",
                parameters={
                    "metric": ParameterSchema(
                        name="metric",
                        type="string",
                        enum=["euclidean", "cosine", "mahalanobis"],
                        default="euclidean",
                        required=False,
                    ),
                    "columns_a": ParameterSchema(
                        name="columns_a",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns for table_a",
                        required=False,
                    ),
                    "columns_b": ParameterSchema(
                        name="columns_b",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns for table_b",
                        required=False,
                    ),
                    "vi_strategy": ParameterSchema(
                        name="vi_strategy",
                        type="string",
                        enum=["auto", "from_a", "from_ab", "from_param"],
                        default="auto",
                        required=False,
                    ),
                    "vi": ParameterSchema(
                        name="vi",
                        type="array",
                        items={"type": "array", "items": {"type": "number"}},
                        description="Inverse covariance matrix for mahalanobis when vi_strategy='from_param'",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_PAIR_TO_FILE,
                tags=["spatial", "distance"],
            )
        )

        # 2. Voronoi
        results.append(
            FunctionMetadata(
                name="Voronoi",
                module="scipy.spatial",
                qualified_name="scipy.spatial.Voronoi",
                fn_id="scipy.spatial.Voronoi",
                source_adapter="scipy_spatial",
                description="Compute the Voronoi diagram of a set of points.",
                parameters={
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_TO_JSON,
                tags=["spatial", "tessellation"],
            )
        )

        # 3. Delaunay
        results.append(
            FunctionMetadata(
                name="Delaunay",
                module="scipy.spatial",
                qualified_name="scipy.spatial.Delaunay",
                fn_id="scipy.spatial.Delaunay",
                source_adapter="scipy_spatial",
                description="Compute the Delaunay triangulation of a set of points.",
                parameters={
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_TO_JSON,
                tags=["spatial", "tessellation"],
            )
        )

        # 4. scipy.spatial.cKDTree
        results.append(
            FunctionMetadata(
                name="cKDTree",
                module="scipy.spatial",
                qualified_name="scipy.spatial.cKDTree",
                fn_id="scipy.spatial.cKDTree",
                source_adapter="scipy_spatial",
                description="kd-tree for quick nearest-neighbor lookup.",
                parameters={
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns",
                        required=False,
                    ),
                    "leafsize": ParameterSchema(
                        name="leafsize",
                        type="integer",
                        default=10,
                        required=False,
                    ),
                    "balanced_tree": ParameterSchema(
                        name="balanced_tree",
                        type="boolean",
                        default=True,
                        required=False,
                    ),
                    "compact_nodes": ParameterSchema(
                        name="compact_nodes",
                        type="boolean",
                        default=True,
                        required=False,
                    ),
                },
                io_pattern=IOPattern.TABLE_TO_OBJECT,
                tags=["spatial", "kdtree", "index"],
            )
        )

        # 5. scipy.spatial.cKDTree.query
        results.append(
            FunctionMetadata(
                name="query",
                module="scipy.spatial.cKDTree",
                qualified_name="scipy.spatial.cKDTree.query",
                fn_id="scipy.spatial.cKDTree.query",
                source_adapter="scipy_spatial",
                description="Query the kd-tree for nearest neighbors.",
                parameters={
                    "k": ParameterSchema(
                        name="k",
                        type="integer",
                        default=1,
                        required=False,
                    ),
                    "eps": ParameterSchema(
                        name="eps",
                        type="number",
                        default=0.0,
                        required=False,
                    ),
                    "p": ParameterSchema(
                        name="p",
                        type="number",
                        default=2.0,
                        required=False,
                    ),
                    "distance_upper_bound": ParameterSchema(
                        name="distance_upper_bound",
                        type="number",
                        required=False,
                    ),
                    "workers": ParameterSchema(
                        name="workers",
                        type="integer",
                        required=False,
                    ),
                    "columns": ParameterSchema(
                        name="columns",
                        type="array",
                        items={"type": "string"},
                        description="Coordinate columns for the query points",
                        required=False,
                    ),
                },
                io_pattern=IOPattern.OBJECT_AND_TABLE_TO_JSON,
                tags=["spatial", "kdtree", "nearest-neighbor"],
            )
        )

        return results

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute spatial functions."""
        if fn_id == "scipy.spatial.distance.cdist":
            return self._execute_cdist(inputs, params, work_dir)
        elif fn_id == "scipy.spatial.Voronoi":
            return self._execute_tessellation(fn_id, inputs, params, work_dir)
        elif fn_id == "scipy.spatial.Delaunay":
            return self._execute_tessellation(fn_id, inputs, params, work_dir)
        elif fn_id == "scipy.spatial.cKDTree":
            return self._execute_kdtree_build(inputs, params)
        elif fn_id == "scipy.spatial.cKDTree.query":
            return self._execute_kdtree_query(inputs, params, work_dir)

        raise ValueError(f"Unsupported spatial fn_id: {fn_id}")

    def _execute_kdtree_build(
        self,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
    ) -> list[dict]:
        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        pa = PandasAdapterForRegistry()
        input_dict = dict(inputs)

        table = input_dict.get("table")
        if table is None:
            # Fallback: try to find any TableRef-like input
            for _name, val in inputs:
                if isinstance(val, dict) and any(
                    k in val for k in ("ref_id", "uri", "path", "type")
                ):
                    table = val
                    break

        if table is None:
            raise ValueError("scipy.spatial.cKDTree requires a table input")

        columns = params.pop("columns", None)
        leafsize = params.pop("leafsize", 10)
        balanced_tree = params.pop("balanced_tree", True)
        compact_nodes = params.pop("compact_nodes", True)

        df = pa._load_table(table)
        selected_cols = (
            columns if columns else df.select_dtypes(include=[np.number]).columns.tolist()
        )
        if len(selected_cols) < 1:
            raise ValueError(f"Table must have at least 1 numeric column, found: {selected_cols}")

        points = df[selected_cols].to_numpy()

        import scipy.spatial

        tree = scipy.spatial.cKDTree(
            points,
            leafsize=leafsize,
            balanced_tree=balanced_tree,
            compact_nodes=compact_nodes,
        )

        uid = uuid.uuid4().hex
        uri = f"obj://default/scipy_spatial/{uid}"
        OBJECT_CACHE.set(uri, tree)

        return [
            {
                "ref_id": uid,
                "type": "ObjectRef",
                "python_class": "scipy.spatial.cKDTree",
                "uri": uri,
                "storage_type": "memory",
                "metadata": {
                    "n_points": tree.n,
                    "n_dims": tree.m,
                    "selected_columns": selected_cols,
                },
            }
        ]

    def _execute_kdtree_query(
        self,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        pa = PandasAdapterForRegistry()
        input_dict = dict(inputs)

        obj_ref = input_dict.get("object")
        table = input_dict.get("table")

        if obj_ref is None or table is None:
            raise ValueError("scipy.spatial.cKDTree.query requires 'object' and 'table' inputs")

        uri = obj_ref.get("uri")
        if not uri or not uri.startswith("obj://"):
            raise ValueError(f"Invalid or missing ObjectRef URI: {uri}")

        tree = OBJECT_CACHE.get(uri)
        if tree is None:
            raise ValueError(f"Object not found in cache: {uri}")

        columns = params.pop("columns", None)
        k = params.pop("k", 1)
        eps = params.pop("eps", 0.0)
        p = params.pop("p", 2.0)
        distance_upper_bound = params.pop("distance_upper_bound", np.inf)
        workers = params.pop("workers", 1)

        df = pa._load_table(table)
        selected_cols = (
            columns if columns else df.select_dtypes(include=[np.number]).columns.tolist()
        )

        query_points = df[selected_cols].to_numpy()

        dists, idxs = tree.query(
            query_points,
            k=k,
            eps=eps,
            p=p,
            distance_upper_bound=distance_upper_bound,
            workers=workers,
        )

        payload = {
            "k": k,
            "shape": list(dists.shape),
            "distances": dists.tolist(),
            "indices": idxs.tolist(),
            "selected_columns": selected_cols,
        }

        ref = self._save_json(
            payload,
            work_dir=work_dir,
            filename="kdtree_query.json",
            metadata_override={
                "fn_id": "scipy.spatial.cKDTree.query",
                "k": k,
                "n_queries": len(query_points),
            },
        )
        return [ref]

        # KDTree execution lands in 09-03
        raise ValueError(f"Unsupported spatial fn_id: {fn_id}")

    def _execute_cdist(
        self,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        pa = PandasAdapterForRegistry()
        input_dict = dict(inputs)

        table_a = input_dict.get("table_a")
        table_b = input_dict.get("table_b")
        if table_a is None or table_b is None:
            raise ValueError("cdist requires table_a and table_b inputs")

        columns_a = params.pop("columns_a", None)
        columns_b = params.pop("columns_b", None)
        metric = params.pop("metric", "euclidean")
        vi_strategy = params.pop("vi_strategy", "auto")
        vi = params.pop("vi", None)

        df_a = pa._load_table(table_a)
        df_b = pa._load_table(table_b)

        xa_cols = (
            columns_a if columns_a else df_a.select_dtypes(include=[np.number]).columns.tolist()
        )
        xb_cols = (
            columns_b if columns_b else df_b.select_dtypes(include=[np.number]).columns.tolist()
        )

        if len(xa_cols) < 2:
            raise ValueError(f"table_a must have at least 2 numeric columns, found: {xa_cols}")
        if len(xb_cols) < 2:
            raise ValueError(f"table_b must have at least 2 numeric columns, found: {xb_cols}")

        if len(xa_cols) != len(xb_cols):
            raise ValueError(
                f"table_a ({len(xa_cols)}) and table_b ({len(xb_cols)}) "
                "must have same number of coordinate columns"
            )

        XA = df_a[xa_cols].to_numpy()
        XB = df_b[xb_cols].to_numpy()

        cdist_kwargs = {}
        if metric == "mahalanobis":
            VI = None
            if vi_strategy == "from_param":
                if vi is None:
                    raise ValueError("vi must be provided when vi_strategy='from_param'")
                VI = np.asarray(vi)
            elif vi_strategy == "from_a":
                VI = np.linalg.inv(np.cov(XA.T))
            elif vi_strategy == "from_ab" or vi_strategy == "auto":
                VI = np.linalg.inv(np.cov(np.vstack([XA, XB]).T))

            if VI is not None:
                cdist_kwargs["VI"] = VI

        import scipy.spatial.distance

        distances = scipy.spatial.distance.cdist(XA, XB, metric=metric, **cdist_kwargs)

        if work_dir is None:
            import tempfile

            work_dir = Path(tempfile.gettempdir())
        else:
            work_dir.mkdir(parents=True, exist_ok=True)

        path = work_dir / "cdist.npy"
        np.save(path, distances)

        metadata = {
            "metric": metric,
            "shape": list(distances.shape),
            "columns_a": xa_cols,
            "columns_b": xb_cols,
        }
        if metric == "mahalanobis":
            metadata["vi_strategy"] = vi_strategy

        return [
            {
                "type": "NativeOutputRef",
                "format": "npy",
                "uri": path.absolute().as_uri(),
                "path": str(path.absolute()),
                "metadata": metadata,
            }
        ]

    def _execute_tessellation(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

        pa = PandasAdapterForRegistry()
        input_dict = dict(inputs)

        table = input_dict.get("table")
        if table is None:
            for _name, val in inputs:
                if isinstance(val, dict) and any(
                    k in val for k in ("ref_id", "uri", "path", "type")
                ):
                    table = val
                    break

        if table is None:
            raise ValueError(f"{fn_id} requires a table input")

        columns = params.pop("columns", None)
        df = pa._load_table(table)

        selected_cols = (
            columns if columns else df.select_dtypes(include=[np.number]).columns.tolist()
        )
        if len(selected_cols) < 2:
            raise ValueError(f"Table must have at least 2 numeric columns, found: {selected_cols}")

        points = df[selected_cols].to_numpy()

        import scipy.spatial

        payload = {"selected_columns": selected_cols}

        if fn_id == "scipy.spatial.Voronoi":
            obj = scipy.spatial.Voronoi(points)
            payload.update(
                {
                    "vertices": obj.vertices,
                    "ridge_points": obj.ridge_points,
                    "ridge_vertices": obj.ridge_vertices,
                    "regions": obj.regions,
                    "point_region": obj.point_region,
                }
            )
            filename = "voronoi.json"
        elif fn_id == "scipy.spatial.Delaunay":
            obj = scipy.spatial.Delaunay(points)
            payload.update(
                {
                    "simplices": obj.simplices,
                    "neighbors": obj.neighbors,
                }
            )
            filename = "delaunay.json"
        else:
            raise ValueError(f"Unsupported tessellation: {fn_id}")

        ref = self._save_json(
            payload,
            work_dir=work_dir,
            filename=filename,
            metadata_override={"fn_id": fn_id, "selected_columns": selected_cols},
        )
        return [ref]

    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern."""
        if func_name == "cdist":
            return IOPattern.TABLE_PAIR_TO_FILE
        if func_name in ("Voronoi", "Delaunay"):
            return IOPattern.TABLE_TO_JSON
        return IOPattern.GENERIC

    def generate_dimension_hints(
        self, module_name: str, func_name: str
    ) -> DimensionRequirement | None:
        """Generate dimension hints."""
        return None
