from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern, ParameterSchema

logger = logging.getLogger(__name__)


class ScipyStatsAdapter(ScipyNdimageAdapter):
    """Adapter for exposing scipy.stats functions dynamically."""

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover functions from configured modules."""
        modules = module_config.get("modules", [])
        if "scipy.stats" not in modules:
            return super().discover(module_config)

        results = []

        # 1. Summary statistics
        for name in ["describe_table", "mean_table", "tmean_table", "skew_table", "kurtosis_table"]:
            results.append(self._create_stats_wrapper_metadata(name))

        # 2. Statistical tests
        for name in [
            "ttest_1samp_table",
            "ttest_ind_table",
            "ttest_rel_table",
            "f_oneway_table",
            "ks_2samp_table",
        ]:
            results.append(self._create_test_wrapper_metadata(name))

        # 3. Distributions
        curated_dists = [
            "norm",
            "expon",
            "gamma",
            "beta",
            "t",
            "chi2",
            "uniform",
            "lognorm",
            "poisson",
            "binom",
        ]
        for dist_name in curated_dists:
            results.extend(self._create_dist_metadata(dist_name))

        return results

    def _create_stats_wrapper_metadata(self, name: str) -> FunctionMetadata:
        params = {
            "column": ParameterSchema(
                name="column",
                type="string",
                description="Column to select if the table has multiple columns",
                required=False,
            ),
            "nan_policy": ParameterSchema(
                name="nan_policy",
                type="string",
                description="NaN policy",
                enum=["propagate", "omit", "raise"],
                default="propagate",
                required=False,
            ),
        }
        return FunctionMetadata(
            name=name,
            module="scipy.stats",
            qualified_name=f"scipy.stats.{name}",
            fn_id=f"scipy.stats.{name}",
            source_adapter="scipy_stats",
            description=f"Compute {name.replace('_table', '')} for a table column.",
            parameters=params,
            io_pattern=IOPattern.TABLE_TO_JSON,
            tags=["stats", "summary"],
        )

    def _create_test_wrapper_metadata(self, name: str) -> FunctionMetadata:
        io_pattern = IOPattern.TABLE_PAIR_TO_JSON
        if name == "ttest_1samp_table":
            io_pattern = IOPattern.TABLE_TO_JSON
        elif name == "f_oneway_table":
            io_pattern = IOPattern.MULTI_TABLE_TO_JSON

        params = {
            "column": ParameterSchema(
                name="column",
                type="string",
                description="Column to select if the table has multiple columns",
                required=False,
            ),
            "nan_policy": ParameterSchema(
                name="nan_policy",
                type="string",
                description="NaN policy",
                enum=["propagate", "omit", "raise"],
                default="propagate",
                required=False,
            ),
        }

        if "ttest" in name:
            params["alternative"] = ParameterSchema(
                name="alternative",
                type="string",
                enum=["two-sided", "less", "greater"],
                default="two-sided",
                required=False,
            )
            if name == "ttest_ind_table":
                params["equal_var"] = ParameterSchema(
                    name="equal_var", type="boolean", default=True, required=False
                )

        return FunctionMetadata(
            name=name,
            module="scipy.stats",
            qualified_name=f"scipy.stats.{name}",
            fn_id=f"scipy.stats.{name}",
            source_adapter="scipy_stats",
            description=f"Run {name.replace('_table', '')} on table data.",
            parameters=params,
            io_pattern=io_pattern,
            tags=["stats", "hypothesis-test"],
        )

    def _create_dist_metadata(self, dist_name: str) -> list[FunctionMetadata]:
        methods = ["pdf", "cdf", "ppf"]
        discrete_dists = ["poisson", "binom"]
        if dist_name in discrete_dists:
            methods = ["pmf", "cdf", "ppf"]

        results = []
        for method in methods:
            params = {
                "args": ParameterSchema(
                    name="args",
                    type="array",
                    items={"type": "number"},
                    description="Shape parameters",
                    required=False,
                ),
                "loc": ParameterSchema(name="loc", type="number", default=0, required=False),
                "scale": ParameterSchema(name="scale", type="number", default=1, required=False),
            }
            if method == "ppf":
                params["p"] = ParameterSchema(
                    name="p",
                    type="array",
                    items={"type": "number"},
                    description="Probabilities",
                    required=True,
                )
            else:
                params["x"] = ParameterSchema(
                    name="x",
                    type="array",
                    items={"type": "number"},
                    description="Quantiles",
                    required=True,
                )

            results.append(
                FunctionMetadata(
                    name=f"{dist_name}.{method}",
                    module="scipy.stats",
                    qualified_name=f"scipy.stats.{dist_name}.{method}",
                    fn_id=f"scipy.stats.{dist_name}.{method}",
                    source_adapter="scipy_stats",
                    description=f"Compute {method.upper()} for {dist_name} distribution.",
                    parameters=params,
                    io_pattern=IOPattern.PARAMS_TO_JSON,
                    tags=["stats", "distribution"],
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
        """Execute scipy.stats function with tabular or image inputs."""
        # 1. Handle distributions
        if fn_id.startswith("scipy.stats.") and len(fn_id.split(".")) >= 4:
            # e.g. scipy.stats.norm.pdf
            return self._execute_distribution(fn_id, params, work_dir)

        # 2. Handle table wrappers
        if fn_id.endswith("_table"):
            return self._execute_table_wrapper(fn_id, inputs, params, work_dir)

        # 3. Fallback to base execution for original scipy.stats functions if needed
        return super().execute(fn_id, inputs, params, work_dir)

    def _load_column(
        self, artifact: Any, column: str | None, nan_policy: str
    ) -> tuple[np.ndarray, str]:
        # Load as dataframe
        try:
            from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

            pa = PandasAdapterForRegistry()
            df = pa._load_table(artifact)
        except Exception:
            # Fallback to loading image data as flat array
            data = self._load_image(artifact)
            data = data.flatten()
            import pandas as pd

            df = pd.DataFrame({"data": data})

        if column and column in df.columns:
            selected_col = column
        else:
            # Auto-select first numeric column
            numeric_df = df.select_dtypes(include=[np.number])
            if not numeric_df.empty:
                selected_col = numeric_df.columns[0]
            else:
                selected_col = df.columns[0]

        series = df[selected_col]

        if nan_policy == "omit":
            series = series.dropna()
        elif nan_policy == "raise":
            if series.isna().any():
                raise ValueError(f"NaNs found in column {selected_col}")

        return series.values, selected_col

    def _execute_table_wrapper(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        input_dict = dict(inputs)
        column = params.pop("column", None)
        nan_policy = params.pop("nan_policy", "propagate")

        data_args = []
        selected_columns = []

        if "table" in input_dict:
            val, col = self._load_column(input_dict["table"], column, nan_policy)
            data_args.append(val)
            selected_columns.append(col)
        elif "table_a" in input_dict and "table_b" in input_dict:
            val_a, col_a = self._load_column(input_dict["table_a"], column, nan_policy)
            val_b, col_b = self._load_column(input_dict["table_b"], column, nan_policy)
            data_args.append(val_a)
            data_args.append(val_b)
            selected_columns.append(col_a)
            selected_columns.append(col_b)
        elif "tables" in input_dict:
            tables = input_dict["tables"]
            if not isinstance(tables, list):
                tables = [tables]
            for t in tables:
                val, col = self._load_column(t, column, nan_policy)
                data_args.append(val)
                selected_columns.append(col)
        elif "image" in input_dict:
            val, col = self._load_column(input_dict["image"], column, nan_policy)
            data_args.append(val)
            selected_columns.append(col)

        # Call underlying scipy function
        base_name = fn_id.replace("_table", "").split(".")[-1]
        import scipy.stats

        if base_name == "mean":
            if not data_args:
                raise ValueError("No data provided for mean_table")
            result = np.mean(data_args[0])
        else:
            func = getattr(scipy.stats, base_name)
            result = func(*data_args, **params)

        # Prepare payload
        payload = {
            "fn_id": fn_id,
            "selected_columns": selected_columns,
            "column": column,
            "nan_policy": nan_policy,
        }
        payload.update(params)

        # Add sample sizes
        if len(data_args) >= 1:
            payload["n_a"] = len(data_args[0])
        if len(data_args) >= 2:
            payload["n_b"] = len(data_args[1])

        # Handle Bunch or other structured returns from scipy
        if hasattr(result, "_asdict"):
            payload.update(result._asdict())
        elif hasattr(result, "__dict__"):
            for k, v in result.__dict__.items():
                if not k.startswith("_"):
                    payload[k] = v

        if not hasattr(result, "_asdict") and hasattr(result, "statistic"):
            payload["statistic"] = result.statistic
        if not hasattr(result, "_asdict") and hasattr(result, "pvalue"):
            payload["pvalue"] = result.pvalue

        if isinstance(result, (float, int, np.number, np.ndarray)):
            payload["value"] = result

        if len(payload) == 2:
            return [self._save_json(result, work_dir=work_dir)]

        return [self._save_json(payload, work_dir=work_dir)]

    def _execute_distribution(
        self, fn_id: str, params: dict[str, Any], work_dir: Path | None = None
    ) -> list[dict]:
        parts = fn_id.split(".")
        dist_name = parts[-2]
        method_name = parts[-1]

        import scipy.stats

        dist_gen = getattr(scipy.stats, dist_name)

        args = params.pop("args", [])
        loc = params.pop("loc", 0)
        scale = params.pop("scale", 1)

        # Create frozen distribution
        try:
            frozen = dist_gen(*args, loc=loc, scale=scale)
        except TypeError:
            frozen = dist_gen(*args, loc=loc)

        method = getattr(frozen, method_name)

        if method_name == "ppf":
            input_val = params.get("p")
        else:
            input_val = params.get("x")

        result = method(input_val)

        return [self._save_json(result, work_dir=work_dir)]
