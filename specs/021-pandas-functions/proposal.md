# Proposal: Pandas Functions for Bioimage-MCP

**Spec ID**: 021-pandas-functions  
**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2026-01-11  
**Target Version**: 0.3.0

---

## 1. Executive Summary

This proposal adds pandas as a first-class dependency in the base environment, enabling:
1. **Static I/O functions**: `base.io.table.load` and `base.io.table.export` for CSV/TSV handling
2. **Dynamic pandas discovery**: Expose curated pandas DataFrame/Series operations via the same adapter pattern used for xarray

This enables AI agents to perform tabular data manipulation on measurement tables (e.g., from Cellpose segmentation, ImageJ measurements, CellProfiler features) within the bioimage-mcp workflow.

---

## 2. Motivation

### 2.1 Use Cases

| Use Case | Current State | With Pandas |
|----------|---------------|-------------|
| Load Cellpose measurement CSV | Manual path handling | `base.io.table.load` → TableRef |
| Filter cells by area | Not possible | `base.pandas.DataFrame.query` |
| Group by condition, compute mean | Not possible | `base.pandas.DataFrame.groupby` |
| Export filtered results | Manual | `base.io.table.export` |
| Merge measurement tables | Not possible | `base.pandas.merge` |
| Pivot time-series data | Not possible | `base.pandas.DataFrame.pivot` |

### 2.2 Why Pandas (Not Polars or stdlib csv)

| Criterion | stdlib csv | Polars | **Pandas** |
|-----------|------------|--------|------------|
| Type inference | ❌ None | ✅ Fast | ✅ Rich |
| Ecosystem integration | ❌ Limited | ⚠️ Growing | ✅ Universal |
| Already a transitive dep | N/A | ❌ No | ✅ Yes (via bioio) |
| Dynamic API richness | ❌ N/A | ⚠️ Different API | ✅ Well-documented |
| Memory efficiency | ✅ Streaming | ✅ Arrow-based | ⚠️ Moderate |

**Decision**: Pandas is already a transitive dependency via bioio, phasorpy, and other scientific packages. Adding it explicitly has near-zero cost while providing maximum ecosystem compatibility.

---

## 3. Constitution Compliance

### 3.1 Principle Review

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Stable MCP Surface | ✅ Compliant | No new MCP tools; uses existing `run`, `list`, `describe` |
| II. Isolated Tool Execution | ✅ Compliant | Pandas runs in base env subprocess |
| III. Artifact References Only | ✅ Compliant | TableRef I/O, no raw data in messages |
| IV. Reproducibility | ✅ Compliant | Lockfile update required |
| V. Safety & Observability | ✅ Compliant | Path validation via allowlists |
| VI. Test-Driven Development | ✅ Planned | Tests first |

### 3.2 Constitution Amendment Required

**None required.** The current constitution does not prohibit adding pandas to the base environment. Principle II states:

> "Heavy or fragile stacks (PyTorch, TensorFlow, Java/Fiji) MUST NOT be installed into the core server environment."

Pandas is neither heavy (~60MB) nor fragile - it's a stable, mature library that is already a transitive dependency. The core server environment remains unchanged; pandas is only added to the **base tool environment** (`bioimage-mcp-base`), which already includes numpy, scipy, scikit-image, and phasorpy.

---

## 4. Technical Design

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Server                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ list/describe│  │    search    │  │        run           │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Registry (Dynamic Discovery)                  │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │ XarrayAdapter  │  │ PandasAdapter  │  │  SkimageAdapter │   │
│  │ (existing)     │  │ (NEW)          │  │  (existing)     │   │
│  └────────────────┘  └────────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               bioimage-mcp-base (Subprocess)                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  dynamic_dispatch.py                                        │ │
│  │  ├── base.pandas.* → PandasDispatcher                      │ │
│  │  ├── base.xarray.* → XarrayDispatcher                      │ │
│  │  └── base.io.table.* → io.py (static functions)            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 New Files

```
src/bioimage_mcp/registry/dynamic/
├── adapters/
│   └── pandas.py              # NEW: PandasAdapterForRegistry
├── pandas_adapter.py          # NEW: Core pandas execution logic
└── pandas_allowlists.py       # NEW: Curated DataFrame/Series methods

tools/base/
├── bioimage_mcp_base/
│   └── ops/
│       └── io.py              # MODIFY: Add load_table, export_table
└── manifest.yaml              # MODIFY: Add pandas dynamic source + static I/O functions

envs/
└── bioimage-mcp-base.yaml     # MODIFY: Add pandas dependency
```

### 4.3 Manifest Configuration

Add to `tools/base/manifest.yaml`:

```yaml
dynamic_sources:
  # ... existing xarray, skimage, etc ...
  
  - adapter: pandas
    prefix: pandas
    modules: []  # Curated allowlist, not module introspection
    include_patterns:
      - "*"
    exclude_patterns:
      - "_*"
      - "test_*"

functions:
  # ... existing functions ...
  
  - fn_id: base.io.table.load
    tool_id: tools.base
    name: Load delimited table
    description: |
      Load a CSV/TSV or other delimited file into the artifact system as a TableRef.
      Uses pandas for robust parsing, type inference, and NA handling.
      Validates path against filesystem.allowed_read configuration.
    tags: [table, io, load, csv, tsv, pandas]
    input_mode: path
    inputs: []
    outputs:
      - name: table
        artifact_type: TableRef
        description: Loaded table artifact with column metadata
    params_schema:
      type: object
      required: [path]
      properties:
        path:
          type: string
          description: Absolute path to the delimited file
        delimiter:
          type: string
          description: "Field delimiter. Auto-detected if omitted. Common: ',' (CSV), '\\t' (TSV), ';'"
        header:
          type: [integer, "null"]
          default: 0
          description: "Row number to use as header (0-indexed). Use null for no header."
        encoding:
          type: string
          default: "utf-8"
          description: "File encoding (utf-8, latin-1, cp1252)"
        na_values:
          type: array
          items: { type: string }
          description: "Additional values to treat as NA/null"
        dtype:
          type: object
          description: "Column name → dtype mapping for explicit type specification"

  - fn_id: base.io.table.export
    tool_id: tools.base
    name: Export table to delimited file
    description: |
      Export a TableRef artifact to a delimited file format (CSV, TSV).
      Uses pandas for consistent formatting and high-precision numeric output.
    tags: [table, io, export, csv, tsv, pandas]
    input_mode: xarray
    inputs:
      - name: table
        artifact_type: TableRef
        required: true
        description: Table artifact to export
    outputs:
      - name: output
        artifact_type: TableRef
        description: Exported file reference
    params_schema:
      type: object
      properties:
        path:
          type: string
          description: Output path. If omitted, generates in work_dir.
        sep:
          type: string
          default: ","
          description: "Field delimiter"
        index:
          type: boolean
          default: false
          description: Write row index as first column
        encoding:
          type: string
          default: "utf-8"
          description: Output file encoding
        float_format:
          type: string
          default: "%.15g"
          description: Format string for floating-point values
```

### 4.4 Group-Based Pandas Allowlists

Instead of listing every method individually, we use a **category-based allowlist** with a **denylist** for specific dangerous methods. This approach:
- Is easier to maintain as pandas evolves
- Automatically includes new safe methods in allowed categories
- Makes the security model transparent

```python
# src/bioimage_mcp/registry/dynamic/pandas_allowlists.py

from enum import Enum
from typing import Any

class PandasCategory(Enum):
    """Pandas method categories based on official API documentation."""
    ATTRIBUTES = "attributes"           # shape, dtypes, columns, index
    CONVERSION = "conversion"           # astype, copy, infer_objects
    INDEXING = "indexing"               # loc, iloc, head, tail, query, xs
    BINARY_OPS = "binary_ops"           # add, sub, mul, div, eq, gt, lt
    FUNCTION_APP = "function_app"       # apply, map, agg, transform
    GROUPBY = "groupby"                 # groupby, resample, rolling, expanding
    COMPUTATIONS = "computations"       # sum, mean, std, corr, cov, quantile
    REINDEXING = "reindexing"           # reindex, set_index, reset_index, rename
    MISSING_DATA = "missing_data"       # isna, notna, fillna, dropna, interpolate
    RESHAPING = "reshaping"             # pivot, melt, stack, unstack, explode
    SORTING = "sorting"                 # sort_values, sort_index, nlargest
    COMBINING = "combining"             # merge, join, concat
    TIME_SERIES = "time_series"         # shift, diff, pct_change, resample
    STRING_ACCESSOR = "str"             # .str.* methods
    DATETIME_ACCESSOR = "dt"            # .dt.* methods
    CATEGORICAL_ACCESSOR = "cat"        # .cat.* methods


# ============================================================================
# ALLOWED CATEGORIES (enabled by default)
# ============================================================================
PANDAS_ALLOWED_CATEGORIES: set[PandasCategory] = {
    PandasCategory.ATTRIBUTES,
    PandasCategory.CONVERSION,
    PandasCategory.INDEXING,
    PandasCategory.BINARY_OPS,
    PandasCategory.FUNCTION_APP,      # With restrictions (see SPECIAL_METHODS)
    PandasCategory.GROUPBY,           # Returns GroupByRef for chaining
    PandasCategory.COMPUTATIONS,
    PandasCategory.REINDEXING,
    PandasCategory.MISSING_DATA,
    PandasCategory.RESHAPING,
    PandasCategory.SORTING,
    PandasCategory.COMBINING,
    PandasCategory.TIME_SERIES,
    PandasCategory.STRING_ACCESSOR,
    PandasCategory.DATETIME_ACCESSOR,
}


# ============================================================================
# DENYLIST - Methods blocked even within allowed categories
# ============================================================================
PANDAS_DENYLIST: frozenset[str] = frozenset({
    # === Serialization (I/O handled by static functions) ===
    "to_csv", "to_excel", "to_json", "to_parquet", "to_pickle",
    "to_sql", "to_hdf", "to_feather", "to_stata", "to_gbq",
    "to_clipboard", "to_markdown", "to_latex", "to_html",
    "to_xml", "to_string", "to_dict", "to_records",
    
    # === Memory-unsafe (returns raw Python objects) ===
    "to_numpy", "values", "__array__", "array", "to_list", "tolist",
    "item", "items", "iteritems", "iterrows", "itertuples",
    
    # === Arbitrary code execution (fully blocked) ===
    "eval",           # String-to-code execution, no safe subset
    "pipe",           # Arbitrary function chaining
    "transform",      # Can execute arbitrary functions
    "applymap",       # Deprecated, use map
    
    # === Interactive / Display ===
    "plot", "hist", "boxplot", "style",
    "_repr_html_", "_repr_latex_", "info",
    
    # === Deprecated ===
    "append",         # Use pd.concat instead
    "swaplevel",      # Rare, complex
    
    # === System info leakage ===
    "memory_usage",   # Leaks memory info
})


# ============================================================================
# SPECIAL METHODS - Require custom handling with restrictions
# ============================================================================
PANDAS_SPECIAL_METHODS: dict[str, dict[str, Any]] = {
    # --- query(): Allow with auditing ---
    "query": {
        "category": PandasCategory.INDEXING,
        "returns": "ObjectRef",
        "summary": "Query rows using boolean expression string",
        "params": {
            "expr": {"type": "string", "required": True,
                     "description": "Boolean expression (e.g., 'area > 100 and circularity > 0.8')"},
        },
        "restrictions": "All queries are logged for audit. Uses numexpr engine when available.",
        "audit": True,  # Flag to enable query logging
        "bioimage_use": "Filter cells by measurement thresholds",
    },
    
    # --- apply(): Allow only with numpy function names ---
    "apply": {
        "category": PandasCategory.FUNCTION_APP,
        "returns": "ObjectRef",
        "summary": "Apply a numpy function along an axis",
        "params": {
            "func": {"type": "string", "required": True,
                     "description": "Name of numpy function (e.g., 'log', 'sqrt', 'exp', 'abs')"},
            "axis": {"type": "integer", "default": 0,
                     "description": "Axis along which to apply (0=rows, 1=columns)"},
        },
        "restrictions": "Only numpy function names allowed (validated against numpy namespace)",
        "allowed_funcs": [
            # Math
            "abs", "sqrt", "square", "exp", "expm1", "log", "log2", "log10", "log1p",
            "sin", "cos", "tan", "arcsin", "arccos", "arctan",
            "sinh", "cosh", "tanh", "arcsinh", "arccosh", "arctanh",
            "floor", "ceil", "trunc", "rint", "round",
            "sign", "negative", "positive", "reciprocal",
            # Stats (element-wise)
            "isnan", "isinf", "isfinite", "isnat",
        ],
        "bioimage_use": "Compute log-transformed intensities, normalize values",
    },
    
    # --- groupby(): Returns GroupByRef for pandas-style chaining ---
    "groupby": {
        "category": PandasCategory.GROUPBY,
        "returns": "GroupByRef",  # Special ObjectRef subtype
        "summary": "Group DataFrame by column(s) for aggregation",
        "params": {
            "by": {"type": ["string", "array"], "required": True,
                   "description": "Column name(s) to group by"},
            "as_index": {"type": "boolean", "default": True,
                         "description": "Use group labels as index in result"},
            "sort": {"type": "boolean", "default": True,
                     "description": "Sort group keys"},
        },
        "chaining": {
            "allowed_methods": ["mean", "sum", "count", "min", "max", "std", "var",
                               "median", "first", "last", "nunique", "size", "agg",
                               "describe", "quantile"],
            "description": "Call aggregation methods on the returned GroupByRef",
        },
        "bioimage_use": "Group cells by condition/treatment, then compute statistics",
    },
    
    # --- map(): Allow dict mapping or numpy functions ---
    "map": {
        "category": PandasCategory.FUNCTION_APP,
        "returns": "ObjectRef",
        "summary": "Map values using dictionary or numpy function",
        "params": {
            "arg": {"type": ["object", "string"], "required": True,
                    "description": "Dict for value mapping, or numpy function name"},
            "na_action": {"type": "string", "enum": ["ignore", None], "default": None,
                          "description": "How to handle NA values"},
        },
        "restrictions": "Only dict or numpy function names allowed",
        "bioimage_use": "Remap categorical labels, apply transformations",
    },
    
    # --- agg(): Allow with restricted function names ---
    "agg": {
        "category": PandasCategory.FUNCTION_APP,
        "returns": "ObjectRef",
        "summary": "Aggregate using one or more operations",
        "params": {
            "func": {"type": ["string", "array"], "required": True,
                     "description": "Aggregation function name(s): 'mean', 'sum', 'count', etc."},
        },
        "allowed_funcs": [
            "sum", "mean", "median", "min", "max", "std", "var", "sem",
            "count", "nunique", "first", "last", "size",
            "prod", "quantile", "mad", "skew", "kurt",
        ],
        "bioimage_use": "Compute multiple statistics in one call",
    },
    
    # --- Serialization to TableRef ---
    "to_tableref": {
        "category": "serialize",
        "returns": "TableRef",
        "summary": "Convert in-memory DataFrame/ObjectRef to file-backed TableRef",
        "params": {
            "format": {"type": "string", "enum": ["csv", "tsv"], "default": "csv"},
        },
        "bioimage_use": "Materialize results for downstream tools or export",
    },
}


# ============================================================================
# CATEGORY → METHODS MAPPING
# ============================================================================
PANDAS_CATEGORY_METHODS: dict[PandasCategory, list[str]] = {
    PandasCategory.ATTRIBUTES: [
        "shape", "dtypes", "columns", "index", "ndim", "size",
        "empty", "axes", "T", "keys", "values",  # values only for metadata, blocked in denylist
    ],
    PandasCategory.CONVERSION: [
        "astype", "copy", "bool", "convert_dtypes", "infer_objects",
    ],
    PandasCategory.INDEXING: [
        "loc", "iloc", "at", "iat", "head", "tail", "sample",
        "xs", "get", "isin", "where", "mask", "truncate",
        "first", "last", "take", "filter", "query",  # query has special handling
    ],
    PandasCategory.BINARY_OPS: [
        "add", "sub", "mul", "div", "truediv", "floordiv", "mod", "pow",
        "radd", "rsub", "rmul", "rdiv", "rfloordiv", "rmod", "rpow",
        "lt", "gt", "le", "ge", "ne", "eq",
        "combine", "combine_first",
    ],
    PandasCategory.FUNCTION_APP: [
        "apply", "map", "agg", "aggregate",  # All have special handling
    ],
    PandasCategory.GROUPBY: [
        "groupby", "resample", "rolling", "expanding", "ewm",
    ],
    PandasCategory.COMPUTATIONS: [
        "abs", "all", "any", "clip", "corr", "corrwith", "count",
        "cov", "cummax", "cummin", "cumprod", "cumsum",
        "describe", "diff", "kurt", "kurtosis",
        "max", "mean", "median", "min", "mode",
        "nunique", "pct_change", "prod", "product",
        "quantile", "rank", "round", "sem", "skew",
        "std", "sum", "var", "value_counts",
    ],
    PandasCategory.REINDEXING: [
        "add_prefix", "add_suffix", "align",
        "drop", "drop_duplicates", "droplevel",
        "reindex", "reindex_like", "rename", "rename_axis",
        "reset_index", "set_index", "set_axis",
    ],
    PandasCategory.MISSING_DATA: [
        "backfill", "bfill", "dropna", "ffill", "fillna",
        "interpolate", "isna", "isnull", "notna", "notnull",
        "pad", "replace",
    ],
    PandasCategory.RESHAPING: [
        "explode", "melt", "pivot", "pivot_table",
        "squeeze", "stack", "unstack", "transpose",
    ],
    PandasCategory.SORTING: [
        "nlargest", "nsmallest", "sort_index", "sort_values",
    ],
    PandasCategory.COMBINING: [
        "assign", "compare", "join", "merge", "update",
    ],
    PandasCategory.TIME_SERIES: [
        "asfreq", "asof", "between_time", "at_time",
        "first_valid_index", "last_valid_index",
        "shift", "tshift", "tz_convert", "tz_localize",
    ],
    PandasCategory.STRING_ACCESSOR: [
        # .str.* methods - all string operations
        "capitalize", "casefold", "cat", "center", "contains",
        "count", "decode", "encode", "endswith", "extract",
        "extractall", "find", "findall", "fullmatch", "get",
        "index", "isalnum", "isalpha", "isdecimal", "isdigit",
        "islower", "isnumeric", "isspace", "istitle", "isupper",
        "join", "len", "ljust", "lower", "lstrip", "match",
        "normalize", "pad", "partition", "removeprefix", "removesuffix",
        "repeat", "replace", "rfind", "rindex", "rjust", "rpartition",
        "rsplit", "rstrip", "slice", "slice_replace", "split",
        "startswith", "strip", "swapcase", "title", "translate",
        "upper", "wrap", "zfill",
    ],
    PandasCategory.DATETIME_ACCESSOR: [
        # .dt.* properties and methods
        "date", "time", "timetz", "year", "month", "day",
        "hour", "minute", "second", "microsecond", "nanosecond",
        "dayofweek", "day_of_week", "weekday", "dayofyear", "day_of_year",
        "quarter", "is_month_start", "is_month_end",
        "is_quarter_start", "is_quarter_end", "is_year_start", "is_year_end",
        "is_leap_year", "daysinmonth", "days_in_month",
        "tz", "freq", "unit",
        "normalize", "strftime", "round", "floor", "ceil",
        "month_name", "day_name", "total_seconds",
        "to_pydatetime", "to_period", "tz_localize", "tz_convert",
    ],
}


# ============================================================================
# TOP-LEVEL PANDAS FUNCTIONS
# ============================================================================
PANDAS_TOPLEVEL_ALLOWLIST: dict[str, dict[str, Any]] = {
    "merge": {
        "category": "combine",
        "summary": "Merge DataFrames on columns or indices",
        "params": {
            "on": {"type": ["string", "array"], "description": "Column(s) to join on"},
            "how": {"type": "string", "enum": ["left", "right", "outer", "inner", "cross"],
                    "default": "inner"},
            "suffixes": {"type": "array", "default": ["_x", "_y"]},
        },
        "bioimage_use": "Join measurement tables by cell ID or label",
    },
    "concat": {
        "category": "combine",
        "summary": "Concatenate DataFrames along an axis",
        "params": {
            "axis": {"type": "integer", "default": 0, "description": "0=rows, 1=columns"},
            "ignore_index": {"type": "boolean", "default": False},
        },
        "bioimage_use": "Stack measurements from multiple experiments",
    },
    "crosstab": {
        "category": "analysis",
        "summary": "Compute cross-tabulation of two or more factors",
        "bioimage_use": "Count cells by condition × treatment",
    },
    "cut": {
        "category": "binning",
        "summary": "Bin values into discrete intervals",
        "params": {
            "bins": {"type": ["integer", "array"], "required": True},
            "labels": {"type": "array", "description": "Labels for bins"},
        },
        "bioimage_use": "Categorize cells by size (small/medium/large)",
    },
    "qcut": {
        "category": "binning",
        "summary": "Bin values into quantile-based intervals",
        "params": {
            "q": {"type": "integer", "required": True, "description": "Number of quantiles"},
        },
        "bioimage_use": "Categorize by percentile",
    },
    "get_dummies": {
        "category": "encoding",
        "summary": "Convert categorical variable to dummy/indicator variables",
        "bioimage_use": "One-hot encode treatment conditions",
    },
}


# ============================================================================
# GROUPBY AGGREGATION METHODS (allowed on GroupByRef)
# ============================================================================
PANDAS_GROUPBY_METHODS: list[str] = [
    "mean", "sum", "count", "min", "max", "std", "var",
    "median", "first", "last", "nunique", "size",
    "agg", "aggregate", "describe", "quantile",
    "sem", "prod", "cumsum", "cummax", "cummin", "cumprod",
    "diff", "pct_change", "rank", "shift",
    "head", "tail", "nth", "ngroup",
    "apply",  # With same restrictions as DataFrame.apply
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_allowed_methods() -> set[str]:
    """Get all methods from allowed categories, minus denylist."""
    allowed = set()
    for category in PANDAS_ALLOWED_CATEGORIES:
        if category in PANDAS_CATEGORY_METHODS:
            allowed.update(PANDAS_CATEGORY_METHODS[category])
    return allowed - PANDAS_DENYLIST


def is_allowed_method(method_name: str) -> bool:
    """Check if a pandas method is allowed."""
    if method_name in PANDAS_DENYLIST:
        return False
    if method_name in PANDAS_SPECIAL_METHODS:
        return True
    return method_name in get_allowed_methods()


def get_method_info(method_name: str) -> dict[str, Any] | None:
    """Get metadata for a method if allowed."""
    if method_name in PANDAS_SPECIAL_METHODS:
        return PANDAS_SPECIAL_METHODS[method_name]
    if is_allowed_method(method_name):
        # Find category
        for cat, methods in PANDAS_CATEGORY_METHODS.items():
            if method_name in methods:
                return {"category": cat.value, "returns": "ObjectRef"}
    return None


def validate_apply_func(func_name: str) -> bool:
    """Validate that a function name is in the allowed numpy functions."""
    allowed = PANDAS_SPECIAL_METHODS.get("apply", {}).get("allowed_funcs", [])
    return func_name in allowed


def validate_agg_func(func_name: str | list) -> bool:
    """Validate aggregation function name(s)."""
    allowed = PANDAS_SPECIAL_METHODS.get("agg", {}).get("allowed_funcs", [])
    if isinstance(func_name, str):
        return func_name in allowed
    return all(f in allowed for f in func_name)
```

#### 4.4.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **`query()` handling** | Allow with auditing | Extremely useful for filtering; all queries logged for security review |
| **`apply()` handling** | Numpy function names only | Prevents arbitrary code; covers 90% of use cases (log, sqrt, exp, etc.) |
| **`groupby()` handling** | Return `GroupByRef` | Matches pandas syntax: `df.groupby('col').mean()` feels natural |
| **Category-based allowlist** | Enable by category + denylist | Easier maintenance, auto-includes new safe methods |

#### 4.4.2 GroupBy Chaining Pattern

The `groupby()` method returns a `GroupByRef` (special `ObjectRef`) that supports chaining:

```python
# Example workflow (matches pandas syntax):
# 1. Load table
table = run("base.io.table.load", params={"path": "/data/measurements.csv"})

# 2. Create DataFrame ObjectRef
df = run("base.pandas.DataFrame", inputs={"table": table})

# 3. GroupBy returns GroupByRef
grouped = run("base.pandas.DataFrame.groupby", 
              inputs={"df": df}, 
              params={"by": "condition"})

# 4. Aggregate on GroupByRef (pandas-style chaining)
result = run("base.pandas.GroupBy.mean", inputs={"groupby": grouped})

# 5. Materialize to TableRef
output = run("base.pandas.DataFrame.to_tableref", inputs={"df": result})
```

#### 4.4.3 Audit Logging for query()

All `query()` calls are logged with:
- Timestamp
- Session ID
- Query expression
- Input artifact ref_id
- Result row count

```python
# Audit log entry example:
{
    "timestamp": "2026-01-11T10:30:45Z",
    "session_id": "sess_abc123",
    "fn_id": "base.pandas.DataFrame.query",
    "expr": "area > 100 and circularity > 0.8",
    "input_ref_id": "ref_xyz789",
    "result_rows": 1247,
    "audit_category": "pandas_query"
}
```

### 4.5 Adapter Implementation Pattern

Following `XarrayAdapterForRegistry`:

```python
# src/bioimage_mcp/registry/dynamic/adapters/pandas.py

class PandasAdapterForRegistry(BaseAdapter):
    """Adapter for pandas operations."""

    def __init__(self) -> None:
        from bioimage_mcp.registry.dynamic.pandas_allowlists import (
            PANDAS_DATAFRAME_ALLOWLIST,
        )
        self.allowlist = PANDAS_DATAFRAME_ALLOWLIST

    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover pandas functions from allowlists."""
        # Similar to XarrayAdapterForRegistry.discover()
        # Returns FunctionMetadata for each allowed method
        ...

    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[dict]:
        """Execute pandas function."""
        # Load TableRef → pd.DataFrame
        # Execute method
        # Return ObjectRef (for chaining) or TableRef (for to_tableref)
        ...

    def _load_df(self, artifact: Artifact) -> pd.DataFrame:
        """Load DataFrame from TableRef or ObjectRef."""
        uri = artifact.get("uri") if isinstance(artifact, dict) else getattr(artifact, "uri", None)
        
        if uri and uri.startswith("obj://"):
            # Load from memory cache
            if uri not in OBJECT_CACHE:
                raise ValueError(f"Object not found: {uri}")
            return OBJECT_CACHE[uri]
        else:
            # Load from file
            path = uri_to_path(uri)
            # Detect delimiter from artifact metadata or file
            sep = artifact.get("metadata", {}).get("delimiter", ",")
            return pd.read_csv(path, sep=sep)

    def _save_table(self, df: pd.DataFrame, work_dir: Path) -> dict:
        """Save DataFrame to TableRef."""
        out_path = work_dir / f"output_{uuid.uuid4().hex[:8]}.csv"
        df.to_csv(out_path, index=False, float_format="%.15g")
        
        columns = [
            {"name": col, "dtype": str(df[col].dtype)}
            for col in df.columns
        ]
        
        return {
            "type": "TableRef",
            "uri": out_path.as_uri(),
            "path": str(out_path),
            "format": "CSV",
            "metadata": {
                "columns": columns,
                "row_count": len(df),
                "delimiter": ",",
            },
        }
```

### 4.6 Static I/O Functions

```python
# tools/base/bioimage_mcp_base/ops/io.py (additions)

def load_table(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Load a delimited file as TableRef using pandas."""
    import pandas as pd
    
    path = params.get("path")
    if not path:
        raise ValueError("Missing required parameter: path")
    
    resolved_path = validate_read_path(path)
    if not resolved_path.exists():
        raise FileNotFoundIOError(str(resolved_path))
    
    # Build pandas read_csv kwargs
    read_kwargs = {
        "filepath_or_buffer": resolved_path,
        "sep": params.get("delimiter"),  # None = auto-detect via python engine
        "header": params.get("header", 0),
        "encoding": params.get("encoding", "utf-8"),
        "na_values": params.get("na_values"),
        "dtype": params.get("dtype"),
    }
    
    # Auto-detect delimiter if not specified
    if read_kwargs["sep"] is None:
        read_kwargs["sep"] = None  # Let pandas infer with sep=None, engine='python'
        read_kwargs["engine"] = "python"
    
    df = pd.read_csv(**{k: v for k, v in read_kwargs.items() if v is not None})
    
    # Infer delimiter for metadata
    with open(resolved_path, encoding=params.get("encoding", "utf-8")) as f:
        first_line = f.readline()
        if "\t" in first_line:
            detected_sep = "\t"
        elif ";" in first_line:
            detected_sep = ";"
        else:
            detected_sep = ","
    
    # Build column metadata
    columns = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        # Normalize dtype names
        if "int" in dtype_str:
            dtype_str = "int64"
        elif "float" in dtype_str:
            dtype_str = "float64"
        elif dtype_str == "object":
            dtype_str = "string"
        elif dtype_str == "bool":
            dtype_str = "bool"
        columns.append({"name": str(col), "dtype": dtype_str})
    
    ref_id = uuid.uuid4().hex
    ref = {
        "ref_id": ref_id,
        "type": "TableRef",
        "uri": f"file://{resolved_path}",
        "path": str(resolved_path),
        "format": "CSV" if detected_sep == "," else "TSV" if detected_sep == "\t" else "DSV",
        "storage_type": "file",
        "mime_type": "text/csv",
        "size_bytes": resolved_path.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
        "metadata": {
            "columns": columns,
            "row_count": len(df),
            "delimiter": detected_sep,
            "encoding": params.get("encoding", "utf-8"),
        },
    }
    
    return {"outputs": {"table": ref}}


def export_table(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Export TableRef to delimited file using pandas."""
    import pandas as pd
    
    table_ref = inputs.get("table")
    if not table_ref:
        raise ValueError("Missing required input: table")
    
    # Load DataFrame
    if isinstance(table_ref, dict):
        uri = table_ref.get("uri")
        metadata = table_ref.get("metadata", {})
    else:
        uri = getattr(table_ref, "uri", None)
        metadata = getattr(table_ref, "metadata", {}) or {}
    
    if uri and uri.startswith("obj://"):
        # Load from memory
        from bioimage_mcp_base.entrypoint import _OBJECT_CACHE
        if uri not in _OBJECT_CACHE:
            raise ValueError(f"Object not found: {uri}")
        df = _OBJECT_CACHE[uri]
    else:
        # Load from file
        path = uri_to_path(uri)
        sep = metadata.get("delimiter", ",")
        df = pd.read_csv(path, sep=sep)
    
    # Determine output path
    dest_path_str = params.get("path")
    if dest_path_str:
        dest_path = validate_write_path(dest_path_str)
    else:
        sep = params.get("sep", ",")
        ext = ".tsv" if sep == "\t" else ".csv"
        dest_path = work_dir / f"exported_{uuid.uuid4().hex[:8]}{ext}"
    
    # Write
    df.to_csv(
        dest_path,
        sep=params.get("sep", ","),
        index=params.get("index", False),
        encoding=params.get("encoding", "utf-8"),
        float_format=params.get("float_format", "%.15g"),
    )
    
    # Build output ref
    columns = [{"name": str(col), "dtype": str(df[col].dtype)} for col in df.columns]
    
    return {
        "outputs": {
            "output": {
                "ref_id": uuid.uuid4().hex,
                "type": "TableRef",
                "uri": f"file://{dest_path}",
                "path": str(dest_path),
                "format": "CSV" if params.get("sep", ",") == "," else "TSV",
                "storage_type": "file",
                "mime_type": "text/csv",
                "size_bytes": dest_path.stat().st_size,
                "metadata": {
                    "columns": columns,
                    "row_count": len(df),
                    "delimiter": params.get("sep", ","),
                },
            }
        }
    }
```

---

## 5. Environment Changes

### 5.1 Update `envs/bioimage-mcp-base.yaml`

```yaml
dependencies:
  # ... existing ...
  - pandas>=2.0  # ADD THIS LINE
```

### 5.2 Regenerate Lockfile

After approval, run:
```bash
conda-lock -f envs/bioimage-mcp-base.yaml -p linux-64 -p osx-arm64 -p win-64
```

---

## 6. Test Plan (TDD)

### 6.1 Contract Tests

| Test ID | Description |
|---------|-------------|
| C001 | `base.io.table.load` schema matches manifest |
| C002 | `base.io.table.export` schema matches manifest |
| C003 | TableRef metadata includes required fields |
| C004 | Dynamic pandas functions discovered correctly |

### 6.2 Unit Tests

| Test ID | Description |
|---------|-------------|
| U001 | Load simple CSV with auto-detected delimiter |
| U002 | Load TSV with explicit delimiter |
| U003 | Load CSV with custom NA values |
| U004 | Load CSV with explicit dtypes |
| U005 | Load CSV without header row |
| U006 | Load fails for path outside allowlist |
| U007 | Load fails for non-existent file |
| U008 | Export DataFrame to CSV |
| U009 | Export DataFrame to TSV |
| U010 | Export preserves numeric precision |
| U011 | Roundtrip load→export→load preserves data |
| U012 | `base.pandas.DataFrame.query` filters correctly |
| U013 | `base.pandas.DataFrame.groupby` aggregates correctly |
| U014 | `base.pandas.merge` joins tables |
| U015 | ObjectRef chaining works for multi-step operations |

### 6.3 Integration Tests

| Test ID | Description |
|---------|-------------|
| I001 | Load Cellpose measurement CSV, filter, export |
| I002 | Load ImageJ Results.csv format |
| I003 | Merge two measurement tables by label |
| I004 | Full workflow: load → groupby → aggregate → export |

---

## 7. Task Breakdown

| # | Task | Priority | Effort | Dependencies |
|---|------|----------|--------|--------------|
| 1 | Add pandas to `bioimage-mcp-base.yaml` | High | 0.5h | - |
| 2 | Regenerate lockfile | High | 0.5h | 1 |
| 3 | Create `pandas_allowlists.py` | High | 2h | - |
| 4 | Create `adapters/pandas.py` | High | 3h | 3 |
| 5 | Create `pandas_adapter.py` | High | 2h | 4 |
| 6 | Register adapter in `adapters/__init__.py` | High | 0.5h | 4 |
| 7 | Add pandas to `dynamic_dispatch.py` | High | 1h | 4 |
| 8 | Implement `load_table()` in `io.py` | High | 2h | - |
| 9 | Implement `export_table()` in `io.py` | High | 1.5h | 8 |
| 10 | Add function definitions to `manifest.yaml` | High | 1h | 8, 9 |
| 11 | Write contract tests | High | 1.5h | 10 |
| 12 | Write unit tests (TDD) | High | 3h | - |
| 13 | Write integration tests | Medium | 2h | All above |
| 14 | Add sample CSV files to `datasets/` | Medium | 0.5h | - |
| 15 | Update AGENTS.md with table I/O patterns | Low | 0.5h | All above |

**Total Estimated Effort**: ~21 hours

---

## 8. Design Decisions (Resolved)

The following design questions have been resolved:

### 8.1 Resolved Decisions

| # | Question | Decision | Implementation |
|---|----------|----------|----------------|
| 1 | **`query()` handling** | ✅ Allow with auditing | All query expressions logged; uses numexpr when available |
| 2 | **`apply()` handling** | ✅ Numpy function names only | Validated against allowlist of ~30 safe numpy functions |
| 3 | **GroupBy result** | ✅ Return `GroupByRef` for chaining | Matches pandas syntax: `df.groupby('col').mean()` |
| 4 | **Allowlist approach** | ✅ Category-based with denylist | 15 categories enabled, ~30 methods denied |
| 5 | **ObjectRef caching** | Shared cache with pandas prefix | URI: `obj://default/pandas/{id}` |
| 6 | **Large table handling** | Load fully for v1 | Document 100MB soft limit, add warnings |

### 8.2 Remaining Open Questions

1. **Excel support (`.xlsx`)**: Defer to separate proposal (requires `openpyxl` dependency)

2. **Parquet support**: Out of scope for this spec (TableRef remains CSV/TSV delimited only).

3. **Multi-index handling**: Expose MultiIndex operations?
   - **Recommendation**: No for v1, keep API simple with single-level indices

4. **Default NA values**: What values to recognize as NA?
   - **Proposal**: `["", "NA", "N/A", "NaN", "null", "None", "#N/A", "#NA", "-"]`

5. **String accessor methods**: Enable full `.str.*` namespace?
   - **Proposal**: Yes, string methods are safe and useful for label manipulation

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pandas version conflicts | Low | Medium | Pin `pandas>=2.0` which is stable |
| Memory issues with large tables | Medium | High | Document limits, add warnings for >100MB |
| API surface too large | Medium | Low | Start with curated subset, expand based on usage |
| Type inference inconsistencies | Low | Medium | Use pandas defaults, document behavior |

---

## 10. Success Criteria

1. ✅ `base.io.table.load` can load CSV/TSV files as TableRef
2. ✅ `base.io.table.export` can export TableRef to CSV/TSV
3. ✅ Dynamic pandas functions discoverable via `list` and `describe`
4. ✅ At least 20 DataFrame methods work via `run`
5. ✅ ObjectRef chaining works for multi-step operations
6. ✅ All tests pass in TDD manner
7. ✅ Lockfile regenerated successfully

---

## 11. References

- [pandas documentation](https://pandas.pydata.org/docs/)
- [xarray adapter implementation](../src/bioimage_mcp/registry/dynamic/adapters/xarray.py)
- [Constitution](../.specify/memory/constitution.md)
- [TableRef model](../src/bioimage_mcp/artifacts/models.py)
