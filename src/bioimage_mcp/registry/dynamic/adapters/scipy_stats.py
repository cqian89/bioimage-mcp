from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

import numpy as np

from bioimage_mcp.artifacts.base import Artifact
from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern

logger = logging.getLogger(__name__)


class ScipyStatsAdapter(ScipyNdimageAdapter):
    """Adapter for exposing scipy.stats functions dynamically."""

    def determine_io_pattern(self, module_name: str, func_name: str) -> IOPattern:
        """Determine I/O pattern for scipy.stats."""
        # Top-level tests (usually 2+ arrays)
        if func_name.startswith("ttest_") or func_name in (
            "ranksums",
            "mannwhitneyu",
            "f_oneway",
            "alexandergovern",
            "kruskal",
            "friedmanchisquare",
            "brunnermunzel",
            "ansari",
            "mood",
            "levene",
            "bartlett",
            "fligner",
        ):
            return IOPattern.MULTI_TABLE_TO_JSON

        # Summary statistics (usually 1 array)
        if func_name in (
            "skew",
            "kurtosis",
            "mode",
            "describe",
            "sem",
            "variation",
            "iqr",
            "entropy",
            "gmean",
            "hmean",
            "pmean",
            "tmean",
            "tvar",
            "tstd",
            "tsem",
            "moment",
        ):
            return IOPattern.TABLE_TO_JSON

        # Default to table->json for most stats functions as they take data
        return IOPattern.TABLE_TO_JSON

    def _load_data(self, artifact: Artifact) -> np.ndarray:
        """Load artifact as numpy array from BioImageRef, TableRef or ObjectRef."""
        if isinstance(artifact, dict):
            atype = artifact.get("type")
        else:
            atype = getattr(artifact, "type", None)

        if atype == "BioImageRef":
            return self._load_image(artifact)

        # Try loading as table/dataframe
        try:
            from bioimage_mcp.registry.dynamic.adapters.pandas import PandasAdapterForRegistry

            pa = PandasAdapterForRegistry()
            df = pa._load_table(artifact)
            return df.values
        except Exception as e:
            logger.warning(f"Failed to load artifact as table: {e}")
            # Fallback to image load if table load fails
            return self._load_image(artifact)

    def execute(
        self,
        fn_id: str,
        inputs: list[tuple[str, Any]],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute scipy.stats function with tabular or image inputs."""
        input_dict = dict(inputs)

        # Resolve function
        parts = fn_id.split(".")
        if len(parts) < 3:
            raise ValueError(f"Invalid fn_id: {fn_id}")

        module_path = ".".join(parts[:-1])
        func_name = parts[-1]

        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # Load data based on pattern or port names
        data_args = []
        if "tables" in input_dict:
            tables = input_dict["tables"]
            if isinstance(tables, list):
                data_args = [self._load_data(t) for t in tables]
            else:
                data_args = [self._load_data(tables)]
        elif "table" in input_dict:
            data_args = [self._load_data(input_dict["table"])]
        elif "image" in input_dict:
            data_args = [self._load_data(input_dict["image"])]

        # Call function
        # scipy.stats functions typically take data arrays as positional arguments
        result = func(*data_args, **params)

        # Save result as JSON
        # ScipyNdimageAdapter._save_json handles recursive conversion of
        # numpy types and nested structures to native JSON-serializable types.
        return [self._save_json(result, work_dir=work_dir)]
