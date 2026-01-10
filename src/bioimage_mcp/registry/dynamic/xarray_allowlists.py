from enum import Enum
from typing import Any


class XarrayFunctionType(Enum):
    TOPLEVEL = "toplevel"  # xr.concat, xr.where
    UFUNC = "ufunc"  # Element-wise operations
    DATAARRAY_CLASS = "class"  # DataArray constructor → ObjectRef
    DATAARRAY_METHOD = "method"  # da.mean(), da.transpose()
    ACCESSOR = "accessor"  # da.rolling().mean()


class SignatureType(Enum):
    SINGLE_INPUT = "single"  # One DataArray in, one out
    MULTI_INPUT = "multi"  # Multiple DataArrays (concat, merge)
    BINARY = "binary"  # Two DataArrays (add, subtract)
    CONSTRUCTOR = "constructor"  # Returns ObjectRef
    INSTANCE_METHOD = "instance"  # Takes ObjectRef, returns artifact
    SPECIAL = "special"  # Complex signatures (apply_ufunc)


# === DATAARRAY CLASS (Constructor) ===
XARRAY_DATAARRAY_CLASS: dict[str, dict[str, Any]] = {
    "DataArray": {
        "category": "constructor",
        "signature_type": SignatureType.CONSTRUCTOR,
        "summary": "Instantiate DataArray from BioImageRef, return ObjectRef",
        "tags": ["initialization", "xarray"],
        "inputs": [{"name": "image", "type": "BioImageRef", "required": True}],
        "outputs": [{"name": "da", "type": "ObjectRef"}],
        "params": {},
        "bioimage_use": "Load image once for multiple sequential operations",
    },
}

# === TOP-LEVEL FUNCTIONS ===
XARRAY_TOPLEVEL_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Combining Data
    "concat": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Concatenate arrays along a new or existing dimension",
        "tags": ["combine", "stitch", "xarray"],
        "params": {"dim": "str", "join": "str?", "fill_value": "Any?"},
        "bioimage_use": "Tile stitching, time-series assembly, Z-stack building",
    },
    "merge": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Merge multiple arrays/datasets into one",
        "tags": ["combine", "merge", "xarray"],
        "bioimage_use": "Combine separate channels into multi-channel image",
    },
    "combine_by_coords": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Combine arrays by aligning coordinates automatically",
        "tags": ["combine", "align", "xarray"],
        "bioimage_use": "Automatic tile alignment based on coordinates",
    },
    "combine_nested": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Combine arrays arranged in nested list structure",
        "tags": ["combine", "grid", "xarray"],
        "bioimage_use": "Grid-based tile assembly (e.g., 3x3 mosaic)",
    },
    # Alignment
    "align": {
        "category": "align",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Align arrays to common coordinates",
        "tags": ["align", "coordinates", "xarray"],
        "bioimage_use": "Multi-modal registration, co-registration",
    },
    "broadcast": {
        "category": "align",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Broadcast arrays against each other",
        "tags": ["broadcast", "shape", "xarray"],
        "bioimage_use": "Shape matching for arithmetic operations",
    },
    # Creation
    "zeros_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create zero-filled array matching input shape/coords",
        "tags": ["create", "zeros", "xarray"],
        "bioimage_use": "Initialize empty mask or accumulator",
    },
    "ones_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create ones-filled array matching input shape/coords",
        "tags": ["create", "ones", "xarray"],
        "bioimage_use": "Initialize uniform mask",
    },
    "full_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create array filled with specified value",
        "tags": ["create", "fill", "xarray"],
        "params": {"fill_value": "scalar"},
        "bioimage_use": "Initialize with background value",
    },
    # Computation
    "where": {
        "category": "compute",
        "signature_type": SignatureType.SPECIAL,
        "summary": "Conditional element selection (like np.where)",
        "tags": ["mask", "threshold", "conditional", "xarray"],
        "bioimage_use": "Masking, thresholding, conditional replacement",
    },
    "dot": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Generalized dot product",
        "tags": ["linear_algebra", "matrix", "xarray"],
        "bioimage_use": "Spectral unmixing, linear combinations",
    },
    "cov": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Compute covariance between arrays",
        "tags": ["statistics", "correlation", "xarray"],
        "bioimage_use": "Channel correlation analysis",
    },
    "corr": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Compute Pearson correlation coefficient",
        "tags": ["statistics", "correlation", "xarray"],
        "bioimage_use": "Co-localization analysis between channels",
    },
    "apply_ufunc": {
        "category": "advanced",
        "signature_type": SignatureType.SPECIAL,
        "summary": "Apply NumPy/custom function with dimension handling",
        "tags": ["advanced", "custom", "dask", "xarray"],
        "bioimage_use": "Custom per-pixel operations, Dask-compatible processing",
    },
    "polyval": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Evaluate polynomial at points",
        "tags": ["polynomial", "math", "xarray"],
        "bioimage_use": "Intensity calibration curves",
    },
}

# === UNIVERSAL FUNCTIONS (UFUNCS) ===
XARRAY_UFUNC_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Arithmetic (binary)
    "add": {"category": "arithmetic", "arity": 2, "summary": "Element-wise addition"},
    "subtract": {"category": "arithmetic", "arity": 2, "summary": "Element-wise subtraction"},
    "multiply": {"category": "arithmetic", "arity": 2, "summary": "Element-wise multiplication"},
    "divide": {"category": "arithmetic", "arity": 2, "summary": "Element-wise division"},
    "true_divide": {
        "category": "arithmetic",
        "arity": 2,
        "summary": "Element-wise division (alias)",
    },
    "floor_divide": {
        "category": "arithmetic",
        "arity": 2,
        "summary": "Element-wise floor division",
    },
    "remainder": {"category": "arithmetic", "arity": 2, "summary": "Element-wise remainder"},
    "mod": {"category": "arithmetic", "arity": 2, "summary": "Element-wise modulo"},
    "power": {"category": "arithmetic", "arity": 2, "summary": "Element-wise power"},
    # Unary Math
    "negative": {"category": "unary", "arity": 1, "summary": "Numerical negative"},
    "positive": {"category": "unary", "arity": 1, "summary": "Numerical positive"},
    "absolute": {"category": "unary", "arity": 1, "summary": "Absolute value"},
    "abs": {"category": "unary", "arity": 1, "summary": "Absolute value (alias)"},
    "sqrt": {"category": "unary", "arity": 1, "summary": "Square root"},
    "square": {"category": "unary", "arity": 1, "summary": "Square"},
    "reciprocal": {"category": "unary", "arity": 1, "summary": "Reciprocal (1/x)"},
    "sign": {"category": "unary", "arity": 1, "summary": "Sign of elements"},
    # Exponential / Logarithmic
    "exp": {"category": "exp_log", "arity": 1, "summary": "Exponential (e^x)"},
    "expm1": {"category": "exp_log", "arity": 1, "summary": "exp(x) - 1"},
    "exp2": {"category": "exp_log", "arity": 1, "summary": "2^x"},
    "log": {"category": "exp_log", "arity": 1, "summary": "Natural logarithm"},
    "log1p": {"category": "exp_log", "arity": 1, "summary": "log(1 + x)"},
    "log2": {"category": "exp_log", "arity": 1, "summary": "Base-2 logarithm"},
    "log10": {"category": "exp_log", "arity": 1, "summary": "Base-10 logarithm"},
    # Trigonometric
    "sin": {"category": "trig", "arity": 1, "summary": "Sine"},
    "cos": {"category": "trig", "arity": 1, "summary": "Cosine"},
    "tan": {"category": "trig", "arity": 1, "summary": "Tangent"},
    "arcsin": {"category": "trig", "arity": 1, "summary": "Inverse sine"},
    "arccos": {"category": "trig", "arity": 1, "summary": "Inverse cosine"},
    "arctan": {"category": "trig", "arity": 1, "summary": "Inverse tangent"},
    "arctan2": {"category": "trig", "arity": 2, "summary": "Two-argument arctangent"},
    "hypot": {"category": "trig", "arity": 2, "summary": "Hypotenuse (sqrt(x1^2 + x2^2))"},
    "sinh": {"category": "trig", "arity": 1, "summary": "Hyperbolic sine"},
    "cosh": {"category": "trig", "arity": 1, "summary": "Hyperbolic cosine"},
    "tanh": {"category": "trig", "arity": 1, "summary": "Hyperbolic tangent"},
    "deg2rad": {"category": "trig", "arity": 1, "summary": "Degrees to radians"},
    "rad2deg": {"category": "trig", "arity": 1, "summary": "Radians to degrees"},
    # Rounding
    "floor": {"category": "rounding", "arity": 1, "summary": "Floor"},
    "ceil": {"category": "rounding", "arity": 1, "summary": "Ceiling"},
    "trunc": {"category": "rounding", "arity": 1, "summary": "Truncate"},
    "rint": {"category": "rounding", "arity": 1, "summary": "Round to nearest int"},
    "round": {"category": "rounding", "arity": 1, "summary": "Round"},
    # Comparison (binary, return bool array)
    "maximum": {"category": "comparison", "arity": 2, "summary": "Element-wise maximum"},
    "minimum": {"category": "comparison", "arity": 2, "summary": "Element-wise minimum"},
    "fmax": {"category": "comparison", "arity": 2, "summary": "Element-wise maximum (ignore NaN)"},
    "fmin": {"category": "comparison", "arity": 2, "summary": "Element-wise minimum (ignore NaN)"},
    "greater": {"category": "comparison", "arity": 2, "summary": "Element-wise greater than"},
    "greater_equal": {
        "category": "comparison",
        "arity": 2,
        "summary": "Element-wise greater or equal",
    },
    "less": {"category": "comparison", "arity": 2, "summary": "Element-wise less than"},
    "less_equal": {"category": "comparison", "arity": 2, "summary": "Element-wise less or equal"},
    "equal": {"category": "comparison", "arity": 2, "summary": "Element-wise equality"},
    "not_equal": {"category": "comparison", "arity": 2, "summary": "Element-wise inequality"},
    # Logical
    "logical_and": {"category": "logical", "arity": 2, "summary": "Element-wise logical AND"},
    "logical_or": {"category": "logical", "arity": 2, "summary": "Element-wise logical OR"},
    "logical_xor": {"category": "logical", "arity": 2, "summary": "Element-wise logical XOR"},
    "logical_not": {"category": "logical", "arity": 1, "summary": "Element-wise logical NOT"},
    # Special
    "isnan": {"category": "special", "arity": 1, "summary": "Test for NaN"},
    "isinf": {"category": "special", "arity": 1, "summary": "Test for infinity"},
    "isfinite": {"category": "special", "arity": 1, "summary": "Test for finite"},
    "clip": {"category": "special", "arity": 3, "summary": "Clip values to range"},
}

# === DATAARRAY METHODS (take ObjectRef OR BioImageRef, return ObjectRef) ===
XARRAY_DATAARRAY_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Dimension Manipulation
    "rename": {
        "category": "axis",
        "summary": "Rename dimensions",
        "returns": "BioImageRef",
        "input_types": ["ObjectRef", "BioImageRef"],
        "params": {
            "mapping": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Mapping from old dimension names to new names.",
                "required": True,
            }
        },
    },
    "squeeze": {
        "category": "axis",
        "summary": "Remove singleton dimensions",
        "returns": "BioImageRef",
        "input_types": ["ObjectRef", "BioImageRef"],
        "params": {
            "dim": {
                "type": "string",
                "description": "Optional dimension name to squeeze.",
                "required": False,
            }
        },
    },
    "expand_dims": {
        "category": "axis",
        "summary": "Add new dimension",
        "returns": "BioImageRef",
        "input_types": ["ObjectRef", "BioImageRef"],
        "params": {
            "dim": {"type": "string", "description": "Name for new dimension", "required": True},
            "axis": {
                "type": "integer",
                "description": "Position to insert new dimension (0=first, -1=before last)",
                "required": False,
            },
        },
    },
    "transpose": {
        "category": "axis",
        "summary": "Reorder dimensions",
        "returns": "BioImageRef",
        "input_types": ["ObjectRef", "BioImageRef"],
        "params": {
            "dims": {
                "type": "array",
                "items": {"type": "string"},
                "description": "New order of dimensions",
                "required": True,
            }
        },
    },
    "stack": {
        "category": "axis",
        "summary": "Combine dimensions into MultiIndex",
        "returns": "ObjectRef",
        "input_types": ["ObjectRef", "BioImageRef"],
    },
    "unstack": {
        "category": "axis",
        "summary": "Decompose MultiIndex dimension",
        "returns": "ObjectRef",
        "input_types": ["ObjectRef", "BioImageRef"],
    },
    "swap_dims": {
        "category": "axis",
        "summary": "Swap dimension for coordinate",
        "returns": "ObjectRef",
        "input_types": ["ObjectRef", "BioImageRef"],
    },
    "set_index": {
        "category": "axis",
        "summary": "Set dimension as index",
        "returns": "ObjectRef",
        "input_types": ["ObjectRef", "BioImageRef"],
    },
    "reset_index": {
        "category": "axis",
        "summary": "Reset index to dimension",
        "returns": "ObjectRef",
        "input_types": ["ObjectRef", "BioImageRef"],
    },
    # Indexing / Selection
    "isel": {"category": "selection", "summary": "Select by integer index", "returns": "ObjectRef"},
    "sel": {
        "category": "selection",
        "summary": "Select by coordinate label",
        "returns": "ObjectRef",
    },
    "head": {"category": "selection", "summary": "Select first n elements", "returns": "ObjectRef"},
    "tail": {"category": "selection", "summary": "Select last n elements", "returns": "ObjectRef"},
    "thin": {
        "category": "selection",
        "summary": "Subsample every n-th element",
        "returns": "ObjectRef",
    },
    "drop_sel": {
        "category": "selection",
        "summary": "Drop by coordinate label",
        "returns": "ObjectRef",
    },
    "drop_isel": {
        "category": "selection",
        "summary": "Drop by integer index",
        "returns": "ObjectRef",
    },
    "where": {
        "category": "selection",
        "summary": "Filter by condition (method form)",
        "returns": "ObjectRef",
    },
    "isin": {"category": "selection", "summary": "Check membership", "returns": "ObjectRef"},
    # Reductions
    "max": {"category": "reduction", "summary": "Maximum (e.g., MIP)", "returns": "BioImageRef"},
    "min": {"category": "reduction", "summary": "Minimum", "returns": "BioImageRef"},
    "mean": {"category": "reduction", "summary": "Mean", "returns": "BioImageRef"},
    "sum": {"category": "reduction", "summary": "Sum", "returns": "BioImageRef"},
    "prod": {"category": "reduction", "summary": "Product", "returns": "BioImageRef"},
    "std": {"category": "reduction", "summary": "Standard deviation", "returns": "BioImageRef"},
    "var": {"category": "reduction", "summary": "Variance", "returns": "BioImageRef"},
    "median": {"category": "reduction", "summary": "Median", "returns": "BioImageRef"},
    "count": {"category": "reduction", "summary": "Count non-NaN", "returns": "ObjectRef"},
    "all": {"category": "reduction", "summary": "All True", "returns": "ObjectRef"},
    "any": {"category": "reduction", "summary": "Any True", "returns": "ObjectRef"},
    "quantile": {
        "category": "reduction",
        "summary": "Quantile (percentile)",
        "returns": "ObjectRef",
    },
    "argmax": {"category": "reduction", "summary": "Index of maximum", "returns": "ObjectRef"},
    "argmin": {"category": "reduction", "summary": "Index of minimum", "returns": "ObjectRef"},
    "idxmax": {"category": "reduction", "summary": "Coordinate of maximum", "returns": "ObjectRef"},
    "idxmin": {"category": "reduction", "summary": "Coordinate of minimum", "returns": "ObjectRef"},
    # Cumulative
    "cumsum": {"category": "cumulative", "summary": "Cumulative sum", "returns": "ObjectRef"},
    "cumprod": {"category": "cumulative", "summary": "Cumulative product", "returns": "ObjectRef"},
    # Transforms
    "pad": {"category": "transform", "summary": "Pad along dimensions", "returns": "ObjectRef"},
    "shift": {
        "category": "transform",
        "summary": "Shift data (NaN at edges)",
        "returns": "ObjectRef",
    },
    "roll": {"category": "transform", "summary": "Roll data circularly", "returns": "ObjectRef"},
    "diff": {"category": "transform", "summary": "N-th order difference", "returns": "ObjectRef"},
    "clip": {"category": "transform", "summary": "Clip to range", "returns": "ObjectRef"},
    "astype": {"category": "transform", "summary": "Cast to dtype", "returns": "ObjectRef"},
    "fillna": {"category": "transform", "summary": "Fill NaN values", "returns": "ObjectRef"},
    "ffill": {"category": "transform", "summary": "Forward fill NaN", "returns": "ObjectRef"},
    "bfill": {"category": "transform", "summary": "Backward fill NaN", "returns": "ObjectRef"},
    "dropna": {"category": "transform", "summary": "Drop NaN values", "returns": "ObjectRef"},
    "sortby": {"category": "transform", "summary": "Sort by coordinate", "returns": "ObjectRef"},
    "rank": {"category": "transform", "summary": "Rank values", "returns": "ObjectRef"},
    # Interpolation
    "interp": {
        "category": "interpolation",
        "summary": "Interpolate to new coordinates",
        "returns": "ObjectRef",
    },
    "interp_like": {
        "category": "interpolation",
        "summary": "Interpolate to match another array",
        "returns": "ObjectRef",
    },
    "reindex": {
        "category": "interpolation",
        "summary": "Reindex to new coordinates",
        "returns": "ObjectRef",
    },
    "reindex_like": {
        "category": "interpolation",
        "summary": "Reindex to match another array",
        "returns": "ObjectRef",
    },
    "interpolate_na": {
        "category": "interpolation",
        "summary": "Interpolate over NaN values",
        "returns": "ObjectRef",
    },
    # Calculus
    "differentiate": {
        "category": "calculus",
        "summary": "Differentiate along coordinate",
        "returns": "ObjectRef",
    },
    "integrate": {
        "category": "calculus",
        "summary": "Integrate along coordinate",
        "returns": "ObjectRef",
    },
    # Broadcasting
    "broadcast_like": {
        "category": "broadcast",
        "summary": "Broadcast to match another array",
        "returns": "ObjectRef",
    },
    # Serialization (finalize ObjectRef back to artifact)
    "to_bioimage": {
        "category": "serialize",
        "summary": "Convert ObjectRef to BioImageRef artifact",
        "returns": "BioImageRef",
    },
    # Metadata and Utilities (to reach 71)
    "assign_coords": {
        "category": "metadata",
        "summary": "Assign new coordinates",
        "returns": "ObjectRef",
    },
    "assign_attrs": {
        "category": "metadata",
        "summary": "Assign new attributes",
        "returns": "ObjectRef",
    },
    "copy": {"category": "utility", "summary": "Copy the DataArray", "returns": "ObjectRef"},
    "pipe": {
        "category": "utility",
        "summary": "Apply function to DataArray",
        "returns": "ObjectRef",
    },
    "round": {"category": "transform", "summary": "Round values", "returns": "ObjectRef"},
    "notnull": {
        "category": "selection",
        "summary": "Check for non-NaN values",
        "returns": "ObjectRef",
    },
    "isnull": {"category": "selection", "summary": "Check for NaN values", "returns": "ObjectRef"},
}

# === DENYLIST ===
XARRAY_DENYLIST: frozenset[str] = frozenset(
    {
        # Memory unsafe - loads entire array into RAM
        "values",
        "to_numpy",
        "load",
        "compute",
        "data",
        "item",
        "as_numpy",
        "__array__",
        # Conversion to non-artifact formats
        "to_series",
        "to_dataframe",
        "to_dict",
        "to_pandas",
        "to_netcdf",
        "to_zarr",  # I/O handled separately
        # Interactive / Plotting
        "plot",
        "show",
        "info",
        "_repr_html_",
        # Deprecated
        "drop",  # Use drop_sel/drop_isel
    }
)


def is_allowed_method(method_name: str) -> bool:
    """
    Check if a method name is allowed for dynamic tool generation.

    Args:
        method_name: The name of the method to check.

    Returns:
        True if the method is in XARRAY_DATAARRAY_ALLOWLIST and not in XARRAY_DENYLIST.
    """
    return method_name in XARRAY_DATAARRAY_ALLOWLIST and method_name not in XARRAY_DENYLIST
