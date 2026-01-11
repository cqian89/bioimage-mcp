from enum import Enum
from typing import Any


class PandasFunctionType(Enum):
    TOPLEVEL = "toplevel"  # pd.concat, pd.merge
    DATAFRAME_CLASS = "class"  # DataFrame constructor
    DATAFRAME_METHOD = "method"  # df.query(), df.groupby()
    GROUPBY_METHOD = "groupby"  # g.mean(), g.sum()


class PandasSignatureType(Enum):
    SINGLE_INPUT = "single"  # One TableRef/ObjectRef in, one out
    MULTI_INPUT = "multi"  # Multiple TableRefs/ObjectRefs (concat, merge)
    CONSTRUCTOR = "constructor"  # Returns ObjectRef
    GROUPBY = "groupby"  # Returns GroupBy object as ObjectRef
    AGGREGATION = "aggregation"  # Method on GroupBy object


# === DATAFRAME CLASS ===
PANDAS_DATAFRAME_CLASS: dict[str, dict[str, Any]] = {
    "DataFrame": {
        "category": "constructor",
        "signature_type": PandasSignatureType.CONSTRUCTOR,
        "summary": "Convert TableRef to in-memory DataFrame ObjectRef",
        "tags": ["initialization", "pandas"],
        "inputs": [{"name": "table", "type": "TableRef", "required": True}],
        "outputs": [{"name": "df", "type": "ObjectRef"}],
        "params": {},
        "bioimage_use": "Load table once for multiple sequential operations",
    },
}

# === DATAFRAME METHODS ===
PANDAS_DATAFRAME_METHODS: dict[str, dict[str, Any]] = {
    # Filtering / Selection
    "query": {
        "category": "selection",
        "summary": "Filter rows with a query expression",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "expr": {
                "type": "string",
                "description": "The query string to evaluate.",
                "required": True,
            },
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["filter", "pandas"],
    },
    "filter": {
        "category": "selection",
        "summary": "Subset rows or columns based on labels",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "items": {"type": "array", "items": {"type": "string"}, "required": False},
            "like": {"type": "string", "required": False},
            "regex": {"type": "string", "required": False},
            "axis": {"type": "integer", "default": 1, "required": False},
        },
        "tags": ["subset", "pandas"],
    },
    "head": {
        "category": "selection",
        "summary": "Return the first n rows",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {"n": {"type": "integer", "default": 5, "required": False}},
        "tags": ["preview", "pandas"],
    },
    "tail": {
        "category": "selection",
        "summary": "Return the last n rows",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {"n": {"type": "integer", "default": 5, "required": False}},
        "tags": ["preview", "pandas"],
    },
    "sample": {
        "category": "selection",
        "summary": "Return a random sample of items",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "n": {"type": "integer", "required": False},
            "frac": {"type": "number", "required": False},
            "replace": {"type": "boolean", "default": False, "required": False},
            "random_state": {"type": "integer", "required": False},
        },
        "tags": ["random", "pandas"],
    },
    "isin": {
        "category": "selection",
        "summary": "Whether each element in the DataFrame is contained in values",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["filter", "pandas"],
    },
    "between": {
        "category": "selection",
        "summary": "Return boolean Series equivalent to left <= series <= right",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["filter", "pandas"],
    },
    "duplicated": {
        "category": "selection",
        "summary": "Return boolean Series denoting duplicate rows",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["filter", "pandas"],
    },
    # Missing Values
    "fillna": {
        "category": "cleaning",
        "summary": "Fill NA/NaN values using the specified method",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "value": {"type": "any", "required": False},
            "method": {"type": "string", "required": False},
            "axis": {"type": "integer", "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["impute", "pandas"],
    },
    "dropna": {
        "category": "cleaning",
        "summary": "Remove missing values",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "axis": {"type": "integer", "default": 0, "required": False},
            "how": {"type": "string", "default": "any", "required": False},
            "thresh": {"type": "integer", "required": False},
            "subset": {"type": "array", "items": {"type": "string"}, "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["cleaning", "pandas"],
    },
    "drop_duplicates": {
        "category": "cleaning",
        "summary": "Return DataFrame with duplicate rows removed",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["cleaning", "pandas"],
    },
    # Replacement / Transformation
    "replace": {
        "category": "transform",
        "summary": "Replace values given in to_replace with value",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["transform", "pandas"],
    },
    "apply_numpy": {
        "category": "transform",
        "summary": "Apply a whitelisted numpy function to the DataFrame",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "func": {
                "type": "string",
                "description": "Numpy function name (log, sqrt, exp, abs, sin, cos, tan)",
                "required": True,
            },
            "axis": {"type": "integer", "default": 0, "required": False},
        },
        "tags": ["transform", "math", "pandas"],
    },
    "astype": {
        "category": "transform",
        "summary": "Cast a pandas object to a specified dtype",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "dtype": {"type": "any", "required": True},
            "copy": {"type": "boolean", "default": True, "required": False},
            "errors": {"type": "string", "default": "raise", "required": False},
        },
        "tags": ["cast", "pandas"],
    },
    "rename": {
        "category": "transform",
        "summary": "Alter axes labels",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "columns": {"type": "object", "required": False},
            "index": {"type": "object", "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["metadata", "pandas"],
    },
    "round": {
        "category": "transform",
        "summary": "Round a DataFrame to a variable number of decimal places",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["math", "pandas"],
    },
    "clip": {
        "category": "transform",
        "summary": "Trim values at input threshold(s)",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["math", "pandas"],
    },
    "diff": {
        "category": "transform",
        "summary": "First discrete difference of element",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["math", "pandas"],
    },
    "rank": {
        "category": "transform",
        "summary": "Compute numerical data ranks (1 through n) along axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["math", "pandas"],
    },
    "shift": {
        "category": "transform",
        "summary": "Shift index by desired number of periods with an optional time freq",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["time", "pandas"],
    },
    "transpose": {
        "category": "transform",
        "summary": "Transpose index and columns",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["reshape", "pandas"],
    },
    # Sorting / Index
    "sort_values": {
        "category": "ordering",
        "summary": "Sort by the values along either axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "by": {"type": "any", "required": True},
            "axis": {"type": "integer", "default": 0, "required": False},
            "ascending": {"type": "boolean", "default": True, "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["sort", "pandas"],
    },
    "sort_index": {
        "category": "ordering",
        "summary": "Sort object by labels (along an axis)",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["sort", "pandas"],
    },
    "reset_index": {
        "category": "index",
        "summary": "Reset the index, or a level of it",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "drop": {"type": "boolean", "default": False, "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["index", "pandas"],
    },
    "set_index": {
        "category": "index",
        "summary": "Set the DataFrame index using existing columns",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "keys": {"type": "any", "required": True},
            "drop": {"type": "boolean", "default": True, "required": False},
            "append": {"type": "boolean", "default": False, "required": False},
            "inplace": {"type": "boolean", "default": False, "required": False},
        },
        "tags": ["index", "pandas"],
    },
    "rename_axis": {
        "category": "index",
        "summary": "Set the name of the axis for the index or columns",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
        "tags": ["index", "pandas"],
    },
    # Grouping
    "groupby": {
        "category": "grouping",
        "summary": "Group DataFrame using a mapper or by a Series of columns",
        "returns": "GroupByRef",
        "signature_type": PandasSignatureType.GROUPBY,
        "input_types": ["TableRef", "ObjectRef"],
        "params": {
            "by": {"type": "any", "required": True},
            "axis": {"type": "integer", "default": 0, "required": False},
            "level": {"type": "any", "required": False},
            "as_index": {"type": "boolean", "default": True, "required": False},
            "sort": {"type": "boolean", "default": True, "required": False},
            "group_keys": {"type": "boolean", "default": True, "required": False},
        },
        "tags": ["split", "pandas"],
    },
    # Reductions / Statistics
    "mean": {
        "category": "reduction",
        "summary": "Return the mean of the values over the requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "sum": {
        "category": "reduction",
        "summary": "Return the sum of the values over the requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "count": {
        "category": "reduction",
        "summary": "Count non-NA cells for each column or row",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "std": {
        "category": "reduction",
        "summary": "Return sample standard deviation over requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "var": {
        "category": "reduction",
        "summary": "Return unbiased variance over requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "min": {
        "category": "reduction",
        "summary": "Return the minimum of the values over the requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "max": {
        "category": "reduction",
        "summary": "Return the maximum of the values over the requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "median": {
        "category": "reduction",
        "summary": "Return the median of the values over the requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "quantile": {
        "category": "reduction",
        "summary": "Return values at the given quantile over requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "idxmax": {
        "category": "reduction",
        "summary": "Return index of first occurrence of maximum over requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "idxmin": {
        "category": "reduction",
        "summary": "Return index of first occurrence of minimum over requested axis",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "describe": {
        "category": "statistics",
        "summary": "Generate descriptive statistics",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    # Arithmetic (binary)
    "abs": {
        "category": "arithmetic",
        "summary": "Return a DataFrame with absolute numeric value of each element",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "add": {
        "category": "arithmetic",
        "summary": "Addition of dataframe and other, element-wise",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "sub": {
        "category": "arithmetic",
        "summary": "Subtraction of dataframe and other, element-wise",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "mul": {
        "category": "arithmetic",
        "summary": "Multiplication of dataframe and other, element-wise",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "div": {
        "category": "arithmetic",
        "summary": "Floating division of dataframe and other, element-wise",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    # Reshaping
    "pivot": {
        "category": "reshape",
        "summary": "Return reshaped DataFrame organized by given index / column values",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "melt": {
        "category": "reshape",
        "summary": "Unpivot a DataFrame from wide to long format",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    # Time-series
    "at_time": {
        "category": "selection",
        "summary": "Select values at particular time of day",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "between_time": {
        "category": "selection",
        "summary": "Select values between particular times of day",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    "resample": {
        "category": "grouping",
        "summary": "Resample time-series data",
        "returns": "ObjectRef",
        "input_types": ["TableRef", "ObjectRef"],
    },
    # Finalize
    "to_table": {
        "category": "serialize",
        "summary": "Convert ObjectRef to TableRef artifact",
        "returns": "TableRef",
        "input_types": ["ObjectRef"],
    },
    "to_tableref": {
        "category": "serialize",
        "summary": "Materialize in-memory ObjectRef to file-backed TableRef",
        "returns": "TableRef",
        "input_types": ["ObjectRef"],
        "params": {
            "format": {"type": "string", "default": "csv", "required": False},
        },
        "tags": ["export", "pandas"],
    },
}

# === GROUPBY METHODS ===
PANDAS_GROUPBY_METHODS: dict[str, dict[str, Any]] = {
    "mean": {
        "category": "aggregation",
        "summary": "Compute group mean",
        "params": {"numeric_only": {"type": "boolean", "default": True, "required": False}},
    },
    "sum": {"category": "aggregation", "summary": "Compute group sum"},
    "count": {"category": "aggregation", "summary": "Compute group count"},
    "min": {"category": "aggregation", "summary": "Compute group minimum"},
    "max": {"category": "aggregation", "summary": "Compute group maximum"},
    "std": {"category": "aggregation", "summary": "Compute group standard deviation"},
    "var": {"category": "aggregation", "summary": "Compute group variance"},
    "median": {"category": "aggregation", "summary": "Compute group median"},
    "first": {"category": "aggregation", "summary": "Compute first of group values"},
    "last": {"category": "aggregation", "summary": "Compute last of group values"},
    "size": {"category": "aggregation", "summary": "Compute group sizes"},
    "nunique": {
        "category": "aggregation",
        "summary": "Return number of unique elements in the group",
    },
    "quantile": {"category": "aggregation", "summary": "Return values at the given quantile"},
    "describe": {"category": "statistics", "summary": "Generate descriptive statistics per group"},
    "cumcount": {
        "category": "cumulative",
        "summary": "Number each item in each group from 0 to the length of that group - 1",
    },
    "cummax": {"category": "cumulative", "summary": "Cumulative max for each group"},
    "cummin": {"category": "cumulative", "summary": "Cumulative min for each group"},
    "cumprod": {"category": "cumulative", "summary": "Cumulative product for each group"},
    "cumsum": {"category": "cumulative", "summary": "Cumulative sum for each group"},
    "head": {"category": "selection", "summary": "Return first n rows of each group"},
    "tail": {"category": "selection", "summary": "Return last n rows of each group"},
    "nth": {"category": "selection", "summary": "Take the nth row from each group if n is an int"},
    "agg": {
        "category": "aggregation",
        "summary": "Aggregate using one or more operations over the specified axis",
        "params": {"func": {"type": "any", "required": True}},
    },
}

# === TOP-LEVEL FUNCTIONS ===
PANDAS_TOPLEVEL_FUNCTIONS: dict[str, dict[str, Any]] = {
    "merge": {
        "category": "combine",
        "signature_type": PandasSignatureType.MULTI_INPUT,
        "summary": "Merge DataFrame or named Series objects with a database-style join",
        "tags": ["join", "pandas"],
        "params": {
            "how": {"type": "string", "default": "inner", "required": False},
            "on": {"type": "any", "required": False},
            "left_on": {"type": "any", "required": False},
            "right_on": {"type": "any", "required": False},
        },
    },
    "concat": {
        "category": "combine",
        "signature_type": PandasSignatureType.MULTI_INPUT,
        "summary": "Concatenate pandas objects along a particular axis",
        "tags": ["combine", "pandas"],
        "params": {
            "axis": {"type": "integer", "default": 0, "required": False},
            "join": {"type": "string", "default": "outer", "required": False},
            "ignore_index": {"type": "boolean", "default": False, "required": False},
        },
    },
}

# === DENYLIST ===
PANDAS_DENYLIST: frozenset[str] = frozenset(
    {
        "eval",
        "to_pickle",
        "read_pickle",
        "to_csv",
        "read_csv",
        "to_excel",
        "read_excel",
        "to_sql",
        "read_sql",
        "to_json",
        "read_json",
        "to_html",
        "read_html",
        "to_feather",
        "read_feather",
        "to_parquet",
        "read_parquet",
        "to_stata",
        "read_stata",
        "exec",
        "apply",  # restricted
        "applymap",
        "pipe",  # can be used to exec arbitrary functions
    }
)


def is_allowed_dataframe_method(method_name: str) -> bool:
    """Check if a method name is allowed for DataFrames."""
    return method_name in PANDAS_DATAFRAME_METHODS and method_name not in PANDAS_DENYLIST


def is_allowed_groupby_method(method_name: str) -> bool:
    """Check if a method name is allowed for GroupBy objects."""
    return method_name in PANDAS_GROUPBY_METHODS and method_name not in PANDAS_DENYLIST


def is_allowed_method(method_name: str) -> bool:
    """
    Check if a method name is allowed for dynamic tool generation (DataFrame default).

    Args:
        method_name: The name of the method to check.

    Returns:
        True if the method is in PANDAS_DATAFRAME_METHODS and not in PANDAS_DENYLIST.
    """
    return is_allowed_dataframe_method(method_name)
