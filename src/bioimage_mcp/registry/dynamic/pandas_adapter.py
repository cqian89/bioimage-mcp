from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from bioimage_mcp.errors import BioimageMcpError

# Import will be created in T006
try:
    from bioimage_mcp.registry.dynamic.pandas_allowlists import (
        PANDAS_DATAFRAME_METHODS,
        PANDAS_DENYLIST,
        PANDAS_GROUPBY_METHODS,
    )
except ImportError:
    # Fallback for TDD if T006 hasn't been run yet or files are missing
    PANDAS_DATAFRAME_METHODS = {}
    PANDAS_GROUPBY_METHODS = {}
    PANDAS_DENYLIST = []

logger = logging.getLogger(__name__)

# Configuration for Object Cache
MAX_CACHE_SIZE = 100  # Default max objects
MAX_CACHE_MEMORY_BYTES = 1024 * 1024 * 1024  # 1GB


class LRUCache(dict):
    """Simple LRU cache for DataFrames."""

    def __init__(self, max_size: int = MAX_CACHE_SIZE, max_memory: int = MAX_CACHE_MEMORY_BYTES):
        super().__init__()
        self.max_size = max_size
        self.max_memory = max_memory
        self.access_order = []
        self.current_memory = 0
        self.obj_memory = {}

    def _get_memory_usage(self, value: Any) -> int:
        """Estimate memory usage of an object."""
        try:
            if hasattr(value, "memory_usage"):
                # DataFrame or Series
                if hasattr(value, "sum"):
                    return value.memory_usage(deep=True).sum()
                return value.memory_usage(deep=True)
            elif "groupby" in str(type(value)).lower():
                # GroupBy object doesn't have memory_usage easily,
                # but it references the original DF. We'll use a small constant
                # or estimate based on the underlying object if possible.
                return 1024 * 1024  # 1MB placeholder for GroupBy
            return 1024 * 10  # 10KB placeholder
        except Exception:
            return 1024 * 10

    def __getitem__(self, key):
        if key in self:
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        new_mem = self._get_memory_usage(value)

        if key in self:
            if key in self.access_order:
                self.access_order.remove(key)
            self.current_memory -= self.obj_memory.get(key, 0)

        # Evict until we have space (by count or memory)
        while self.access_order and (
            len(self) >= self.max_size or (self.current_memory + new_mem > self.max_memory)
        ):
            evict_key = self.access_order.pop(0)
            evict_mem = self.obj_memory.get(evict_key, 0)
            logger.warning(
                f"OBJECT_CACHE limit reached (count={len(self)}/{self.max_size}, "
                f"mem={self.current_memory / 1e6:.1f}/{self.max_memory / 1e6:.1f}MB). "
                f"Evicting LRU object: {evict_key}"
            )
            self.current_memory -= evict_mem
            self.obj_memory.pop(evict_key, None)
            if evict_key in self:
                super().__delitem__(evict_key)

        super().__setitem__(key, value)
        self.access_order.append(key)
        self.obj_memory[key] = new_mem
        self.current_memory += new_mem

    def __delitem__(self, key):
        if key in self:
            if key in self.access_order:
                self.access_order.remove(key)
            self.current_memory -= self.obj_memory.get(key, 0)
            self.obj_memory.pop(key, None)
        super().__delitem__(key)

    def clear(self):
        super().clear()
        self.access_order.clear()
        self.current_memory = 0
        self.obj_memory.clear()


# In-memory object cache for pandas DataFrames and GroupBy objects
OBJECT_CACHE = LRUCache(MAX_CACHE_SIZE, MAX_CACHE_MEMORY_BYTES)


class MethodNotAllowedError(BioimageMcpError):
    """Raised when a method is not in the allowlist or is denylisted."""

    code = "METHOD_NOT_ALLOWED"


class PandasQueryError(BioimageMcpError):
    """Raised when a pandas query is invalid or restricted."""

    code = "PANDAS_INVALID_QUERY"


class PandasMissingColumnError(BioimageMcpError):
    """Raised when a requested column is missing from the DataFrame."""

    code = "PANDAS_MISSING_COLUMN"


class ObjectNotFoundError(BioimageMcpError):
    """Raised when an ObjectRef is not found in cache (possibly evicted)."""

    code = "OBJECT_NOT_FOUND"


class PandasAdapter:
    """Adapter for exposing curated pandas methods as MCP tools."""

    def __init__(self, allowlist: dict[str, dict] | None = None):
        self.allowlist = allowlist if allowlist is not None else PANDAS_DATAFRAME_METHODS

    def execute(
        self,
        method_name: str,
        data: pd.DataFrame | str,
        ref_id: str | None = None,
        **kwargs,
    ) -> pd.DataFrame | pd.core.groupby.DataFrameGroupBy:
        """Execute an allowed pandas method on the data."""
        # Handle ObjectRef (URI string)
        if isinstance(data, str) and data.startswith("obj://"):
            ref_id = ref_id or data
            # Check for shared cache in registry adapter (for tests)
            # We import here to avoid circular dependencies
            try:
                import bioimage_mcp.registry.dynamic.adapters.pandas as reg

                cache = getattr(reg, "OBJECT_CACHE", OBJECT_CACHE)
            except (ImportError, ModuleNotFoundError):
                cache = OBJECT_CACHE

            if data not in cache:
                raise ObjectNotFoundError(
                    f"ObjectRef with URI '{data}' not found in cache",
                    details={
                        "hint": "The object may have been evicted. Re-run the operation that created it."
                    },
                )
            data = cache[data]

        # Check denylist first
        if method_name in PANDAS_DENYLIST:
            raise MethodNotAllowedError(
                f"Method '{method_name}' is not allowed (denylisted)",
                details={"method": method_name},
            )

        # Check allowlist
        if method_name not in self.allowlist:
            raise MethodNotAllowedError(
                f"Method '{method_name}' is not in allowlist",
                details={"method": method_name},
            )

        # Special handling for query() - log for audit and block @var
        if method_name == "query":
            expr = kwargs.get("expr", "")
            if "@" in str(expr):
                raise PandasQueryError(
                    "Local variable access via '@' is blocked for security",
                    details={"expr": expr},
                )

        # Special handling for apply_numpy
        if method_name == "apply_numpy":
            return self.apply_numpy(data, **kwargs)

        # Execute method
        if not hasattr(data, method_name):
            raise ValueError(f"Data object does not have method '{method_name}'")

        method = getattr(data, method_name)
        try:
            result = method(**kwargs)
        except KeyError as e:
            if method_name == "groupby":
                available = list(data.columns) if hasattr(data, "columns") else []
                raise PandasMissingColumnError(
                    f"Column '{e.args[0]}' not found",
                    details={"available_columns": available, "missing_column": str(e.args[0])},
                ) from e
            raise
        except Exception as e:
            if method_name == "query":
                raise PandasQueryError(
                    f"Invalid pandas query: {e}",
                    details={"expr": kwargs.get("expr"), "error": str(e)},
                ) from e
            raise

        if method_name == "query":
            row_count = len(result) if hasattr(result, "__len__") else "unknown"
            logger.info(
                f"Executing pandas query: expr={kwargs.get('expr')!r}, "
                f"input={ref_id or 'direct'}, rows={row_count}"
            )

        return result

    def merge(self, left: pd.DataFrame, right: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Merge two DataFrames with structured error handling."""
        try:
            return pd.merge(left, right, **kwargs)
        except KeyError as e:
            col = str(e.args[0])
            # Determine which side is missing the column
            if col not in left.columns:
                available = list(left.columns)
                msg = f"Key column '{col}' not found in left DataFrame"
            elif col not in right.columns:
                available = list(right.columns)
                msg = f"Key column '{col}' not found in right DataFrame"
            else:
                # Should not happen for simple 'on' but maybe for complex ones
                available = list(left.columns) + list(right.columns)
                msg = f"Key column '{col}' not found in DataFrames"

            raise PandasMissingColumnError(
                msg,
                details={
                    "available_columns": available,
                    "hint": "Use one of the available columns as the merge key",
                    "missing_column": col,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error merging DataFrames: {e}")
            raise

    def concat(self, objs: list[pd.DataFrame], **kwargs) -> pd.DataFrame:
        """Concatenate multiple DataFrames."""
        try:
            return pd.concat(objs, **kwargs)
        except Exception as e:
            logger.error(f"Error concatenating DataFrames: {e}")
            raise

    def apply_numpy(self, data: pd.DataFrame, func: str, axis: int = 0) -> pd.DataFrame:
        """Apply a whitelisted numpy function to the DataFrame."""
        allowed_funcs = {
            "log": np.log,
            "sqrt": np.sqrt,
            "exp": np.exp,
            "abs": np.abs,
            "sin": np.sin,
            "cos": np.cos,
            "tan": np.tan,
        }

        if func not in allowed_funcs:
            raise MethodNotAllowedError(
                f"Numpy function '{func}' is not in the allowlist for apply_numpy",
                details={"allowed_functions": list(allowed_funcs.keys()), "requested": func},
            )

        # Ensure numeric data only for math functions
        # Select numeric columns if it's a DataFrame
        if isinstance(data, pd.DataFrame):
            numeric_df = data.select_dtypes(include=[np.number])
            if numeric_df.empty:
                raise ValueError("No numeric columns found in DataFrame for math operation")

            # Apply to numeric columns and preserve others if possible?
            # Usually apply returns just the result of the application.
            # For simplicity, we'll apply to the whole thing if it's numeric,
            # or just numeric columns if it's mixed.
            return numeric_df.apply(allowed_funcs[func], axis=axis)

        return data.apply(allowed_funcs[func])
