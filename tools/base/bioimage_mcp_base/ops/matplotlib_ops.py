from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bioio import BioImage

from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE


def _build_obj_uri(session_id: str, env_id: str, artifact_id: str) -> str:
    """Build properly scoped obj:// URI."""
    return f"obj://{session_id}/{env_id}/{artifact_id}"


def subplots(session_id: str = "default", env_id: str = "base", **params) -> list[dict]:
    """Create subplots and store in cache."""
    fig, ax = plt.subplots(**params)

    fig_id = str(uuid.uuid4())
    fig_uri = _build_obj_uri(session_id, env_id, fig_id)
    OBJECT_CACHE[fig_uri] = fig
    fig._mcp_ref_id = fig_id

    fig_ref = {
        "ref_id": fig_id,
        "type": "FigureRef",
        "python_class": "matplotlib.figure.Figure",
        "uri": fig_uri,
        "storage_type": "memory",
        "metadata": {
            "output_name": "figure",
            "figsize": fig.get_size_inches().tolist(),
            "dpi": int(fig.get_dpi()),
            "axes_count": len(fig.axes),
        },
    }

    results = [fig_ref]

    if isinstance(ax, np.ndarray):
        for i, a in enumerate(ax.flatten()):
            ax_id = str(uuid.uuid4())
            ax_uri = _build_obj_uri(session_id, env_id, ax_id)
            OBJECT_CACHE[ax_uri] = a
            a._mcp_ref_id = ax_id
            results.append(
                {
                    "ref_id": ax_id,
                    "type": "AxesRef",
                    "python_class": "matplotlib.axes._axes.Axes",
                    "uri": ax_uri,
                    "storage_type": "memory",
                    "metadata": {
                        "output_name": f"axes_{i}",
                        "parent_figure_ref_id": fig_id,
                    },
                }
            )
    else:
        ax_id = str(uuid.uuid4())
        ax_uri = _build_obj_uri(session_id, env_id, ax_id)
        OBJECT_CACHE[ax_uri] = ax
        ax._mcp_ref_id = ax_id
        results.append(
            {
                "ref_id": ax_id,
                "type": "AxesRef",
                "python_class": "matplotlib.axes._axes.Axes",
                "uri": ax_uri,
                "storage_type": "memory",
                "metadata": {
                    "output_name": "axes",
                    "parent_figure_ref_id": fig_id,
                },
            }
        )

    return results


def figure(session_id: str = "default", env_id: str = "base", **params) -> list[dict]:
    """Create figure and store in cache."""
    fig = plt.figure(**params)
    fig_id = str(uuid.uuid4())
    fig_uri = _build_obj_uri(session_id, env_id, fig_id)
    OBJECT_CACHE[fig_uri] = fig
    fig._mcp_ref_id = fig_id

    return [
        {
            "ref_id": fig_id,
            "type": "FigureRef",
            "python_class": "matplotlib.figure.Figure",
            "uri": fig_uri,
            "storage_type": "memory",
            "metadata": {
                "output_name": "figure",
                "figsize": fig.get_size_inches().tolist(),
                "dpi": int(fig.get_dpi()),
            },
        }
    ]


def imshow(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Display image on axes."""
    ax = _find_axes(inputs)
    x_val = None

    for name, value in inputs:
        if name == "X":
            x_val = value

    if x_val is None:
        x_val = params.get("X")

    if x_val is None:
        # Check if any other input is a BioImageRef
        for _, value in inputs:
            if isinstance(value, dict) and value.get("type") == "BioImageRef":
                x_val = value
                break

    if x_val is None:
        raise ValueError("Missing 'X' (image data) for imshow")

    # Load image data
    if isinstance(x_val, dict) and x_val.get("type") == "BioImageRef":
        img = BioImage(x_val.get("path"))
        # Get 2D slice (first channel, first Z, first T)
        # bioio.BioImage.data is (T, C, Z, Y, X)
        data = img.data[0, 0, 0, :, :]
    else:
        data = x_val

    # Handle downsampling
    max_display_size = params.get("max_display_size")
    if max_display_size and isinstance(data, np.ndarray):
        h, w = data.shape[:2]
        if max(h, w) > max_display_size:
            scale = max_display_size / max(h, w)
            from scipy.ndimage import zoom

            data = zoom(data, scale, order=1)

    # Filter params
    imshow_params = {k: v for k, v in params.items() if k not in ["X", "max_display_size"]}
    if "origin" not in imshow_params:
        imshow_params["origin"] = "upper"

    im = ax.imshow(data, **imshow_params)

    im_id = str(uuid.uuid4())
    im_uri = _build_obj_uri(session_id, env_id, im_id)
    OBJECT_CACHE[im_uri] = im

    # Get parent axes ref_id
    parent_axes_ref_id = getattr(ax, "_mcp_ref_id", None)

    # Fallback: look for AxesRef in inputs (or ObjectRef that is this axes)
    if not parent_axes_ref_id:
        for _name, value in inputs:
            if isinstance(value, dict) and value.get("ref_id"):
                if value.get("type") == "AxesRef" or _load_object(value) is ax:
                    parent_axes_ref_id = value.get("ref_id")
                    break

    return [
        {
            "ref_id": im_id,
            "type": "AxesImageRef",
            "python_class": "matplotlib.image.AxesImage",
            "uri": im_uri,
            "storage_type": "memory",
            "metadata": {
                "output_name": "axes_image",
                "parent_axes_ref_id": parent_axes_ref_id,
                "cmap": imshow_params.get("cmap", "viridis"),
                "vmin": imshow_params.get("vmin"),
                "vmax": imshow_params.get("vmax"),
                "origin": imshow_params.get("origin", "upper"),
                "interpolation": imshow_params.get("interpolation", "antialiased"),
            },
        }
    ]


def add_patch(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Add patch to axes."""
    ax = _find_axes(inputs)
    patch = None

    for name, value in inputs:
        if name in ["p", "patch"]:
            patch = _load_object(value)

    if not patch:
        patch = _load_object(params.get("p") or params.get("patch"))

    if not patch:
        # Look for ObjectRef with matplotlib.patches.Patch
        for _, value in inputs:
            obj = _load_object(value)
            if isinstance(obj, patches.Patch):
                patch = obj
                break

    if not patch:
        raise ValueError("Missing 'patch' input for add_patch")

    ax.add_patch(patch)
    return []


def create_circle(
    params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Create a Circle patch and store in cache."""
    circle = patches.Circle(**params)

    patch_id = str(uuid.uuid4())
    patch_uri = _build_obj_uri(session_id, env_id, patch_id)
    OBJECT_CACHE[patch_uri] = circle

    return [
        {
            "ref_id": patch_id,
            "type": "ObjectRef",
            "python_class": "matplotlib.patches.Circle",
            "uri": patch_uri,
            "storage_type": "memory",
            "metadata": {"output_name": "output"},
        }
    ]


def create_rectangle(
    params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Create a Rectangle patch and store in cache."""
    rect = patches.Rectangle(**params)

    patch_id = str(uuid.uuid4())
    patch_uri = _build_obj_uri(session_id, env_id, patch_id)
    OBJECT_CACHE[patch_uri] = rect

    return [
        {
            "ref_id": patch_id,
            "type": "ObjectRef",
            "python_class": "matplotlib.patches.Rectangle",
            "uri": patch_uri,
            "storage_type": "memory",
            "metadata": {"output_name": "output"},
        }
    ]


def hist(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Plot histogram on axes."""
    ax = _find_axes(inputs)
    x_val = None

    for name, value in inputs:
        if name == "x":
            x_val = value

    if x_val is None:
        x_val = params.get("x")

    if x_val is None:
        raise ValueError("Missing 'x' (data) for hist")

    data = _resolve_data(x_val, inputs, params)

    # Filter params
    hist_params = {k: v for k, v in params.items() if k != "x"}
    ax.hist(data, **hist_params)

    return []


def plot(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Plot line/markers on axes."""
    ax = _find_axes(inputs)
    x_val = None
    y_val = None

    for name, value in inputs:
        if name == "x":
            x_val = value
        elif name == "y":
            y_val = value

    if x_val is None:
        x_val = params.get("x")
    if y_val is None:
        y_val = params.get("y")

    if x_val is None or y_val is None:
        raise ValueError("Missing 'x' or 'y' data for plot")

    # Find a TableRef if any of x, y are column names
    df = None
    table_art = None
    for _, art in inputs:
        if isinstance(art, dict) and art.get("type") == "TableRef":
            table_art = art
            break

    if table_art:
        df = _load_table(table_art)
        if df.empty:
            ax.plot([], [])
            return []

    # Resolve x, y
    x_data = _resolve_column_or_data(x_val, df, inputs, params)
    y_data = _resolve_column_or_data(y_val, df, inputs, params)

    # Filter params
    fmt = params.get("fmt")
    plot_params = {k: v for k, v in params.items() if k not in ["x", "y", "fmt"]}

    if fmt:
        ax.plot(x_data, y_data, fmt, **plot_params)
    else:
        ax.plot(x_data, y_data, **plot_params)

    return []


def scatter(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Plot scatter on axes."""
    ax = _find_axes(inputs)
    x_val = None
    y_val = None
    s_val = params.get("s")
    c_val = params.get("c")

    for name, value in inputs:
        if name == "x":
            x_val = value
        elif name == "y":
            y_val = value

    if x_val is None:
        x_val = params.get("x")
    if y_val is None:
        y_val = params.get("y")

    if x_val is None or y_val is None:
        raise ValueError("Missing 'x' or 'y' data for scatter")

    # Find a TableRef if any of x, y, s, c are column names
    df = None
    table_art = None
    for _, art in inputs:
        if isinstance(art, dict) and art.get("type") == "TableRef":
            table_art = art
            break

    if table_art:
        df = _load_table(table_art)
        if df.empty:
            ax.scatter([], [])
            return []

    # Resolve x, y, s, c
    x_data = _resolve_column_or_data(x_val, df, inputs, params)
    y_data = _resolve_column_or_data(y_val, df, inputs, params)
    s_data = _resolve_column_or_data(s_val, df, inputs, params)
    c_data = _resolve_column_or_data(c_val, df, inputs, params)

    # Filter params
    scatter_params = {k: v for k, v in params.items() if k not in ["x", "y", "s", "c"]}
    if s_data is not None:
        scatter_params["s"] = s_data
    if c_data is not None:
        scatter_params["c"] = c_data

    ax.scatter(x_data, y_data, **scatter_params)
    return []


def boxplot(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Plot boxplot on axes."""
    ax = _find_axes(inputs)
    x_val = None
    positions_val = params.get("positions")
    labels_val = params.get("labels")

    for name, value in inputs:
        if name == "x":
            x_val = value

    if x_val is None:
        x_val = params.get("x")

    if x_val is None:
        raise ValueError("Missing 'x' (data) for boxplot")

    # Find TableRef
    df = None
    table_art = None
    for _, art in inputs:
        if isinstance(art, dict) and art.get("type") == "TableRef":
            table_art = art
            break

    if table_art:
        df = _load_table(table_art)

    # T037: Handle categorical grouping
    if df is not None and isinstance(positions_val, str) and positions_val in df.columns:
        group_col = positions_val
        data_col = x_val if isinstance(x_val, str) and x_val in df.columns else None

        if data_col:
            groups = df.groupby(group_col)[data_col].apply(list).to_dict()
            labels = labels_val or list(groups.keys())
            labels = [label for label in labels if label in groups]
            data = [groups[label] for label in labels]

            positions = list(range(1, len(data) + 1))

            boxplot_params = {
                k: v for k, v in params.items() if k not in ["x", "positions", "labels"]
            }
            ax.boxplot(data, positions=positions, labels=labels, **boxplot_params)
            return []

    data = _resolve_data(x_val, inputs, params)
    boxplot_params = {k: v for k, v in params.items() if k != "x"}
    ax.boxplot(data, **boxplot_params)
    return []


def violinplot(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Plot violinplot on axes."""
    ax = _find_axes(inputs)
    dataset_val = None
    positions_val = params.get("positions")
    labels_val = params.get("labels")

    for name, value in inputs:
        if name == "dataset":
            dataset_val = value

    if dataset_val is None:
        dataset_val = params.get("dataset")

    if dataset_val is None:
        raise ValueError("Missing 'dataset' for violinplot")

    # Find TableRef
    df = None
    table_art = None
    for _, art in inputs:
        if isinstance(art, dict) and art.get("type") == "TableRef":
            table_art = art
            break

    if table_art:
        df = _load_table(table_art)

    # T037: Handle categorical grouping
    if df is not None and isinstance(positions_val, str) and positions_val in df.columns:
        group_col = positions_val
        data_col = (
            dataset_val if isinstance(dataset_val, str) and dataset_val in df.columns else None
        )

        if data_col:
            groups = df.groupby(group_col)[data_col].apply(list).to_dict()
            labels = labels_val or list(groups.keys())
            labels = [label for label in labels if label in groups]
            data = [groups[label] for label in labels]

            positions = list(range(1, len(data) + 1))

            violin_params = {
                k: v for k, v in params.items() if k not in ["dataset", "positions", "labels"]
            }
            ax.violinplot(data, positions=positions, **violin_params)

            if params.get("vert", True):
                ax.set_xticks(positions)
                ax.set_xticklabels(labels)

            return []

    data = _resolve_data(dataset_val, inputs, params)
    violin_params = {k: v for k, v in params.items() if k != "dataset"}
    ax.violinplot(data, **violin_params)
    return []


def colorbar(
    inputs: list[Any], params: dict[str, Any], session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Add a colorbar to a plot."""
    mappable = None
    ax = None

    for name, value in inputs:
        if name == "mappable":
            mappable = _load_object(value)
        elif name in ["axes", "ax"]:
            ax = _load_object(value)

    if not mappable:
        # Look for any ObjectRef that is a mappable
        for _name, value in inputs:
            obj = _load_object(value)
            if obj and hasattr(obj, "get_cmap"):
                mappable = obj
                break

    if not ax:
        try:
            ax = _find_axes(inputs)
        except ValueError:
            if mappable and hasattr(mappable, "axes"):
                ax = mappable.axes

    if not ax:
        raise ValueError("Missing 'axes' for colorbar")

    fig = ax.figure
    cb_params = {k: v for k, v in params.items() if k not in ["mappable", "ax"]}
    fig.colorbar(mappable, ax=ax, **cb_params)
    return []


def generic_op(
    inputs: list[Any],
    params: dict[str, Any],
    method_name: str,
    session_id: str = "default",
    env_id: str = "base",
) -> list[dict]:
    """Execute a generic method on the first input object."""
    if not inputs:
        raise ValueError(f"Missing input for {method_name}")

    obj = _load_object(inputs[0][1])
    if not obj:
        obj = inputs[0][1]

    if not hasattr(obj, method_name):
        raise ValueError(f"Object {type(obj)} has no method {method_name}")

    method = getattr(obj, method_name)
    res = method(**params)

    if res is None:
        return []

    # If it returns a figure or axes, we should handle it
    if isinstance(res, plt.Figure):
        # Handle Figure (similar to figure() op)
        fig_id = str(uuid.uuid4())
        fig_uri = _build_obj_uri(session_id, env_id, fig_id)
        OBJECT_CACHE[fig_uri] = res
        return [
            {
                "ref_id": fig_id,
                "type": "FigureRef",
                "python_class": "matplotlib.figure.Figure",
                "uri": fig_uri,
                "storage_type": "memory",
                "metadata": {
                    "output_name": "figure",
                    "figsize": res.get_size_inches().tolist(),
                    "dpi": int(res.get_dpi()),
                },
            }
        ]

    # For other returns, return as an ObjectRef
    ref_id = str(uuid.uuid4())
    uri = _build_obj_uri(session_id, env_id, ref_id)
    OBJECT_CACHE[uri] = res
    return [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "python_class": f"{type(res).__module__}.{type(res).__name__}",
            "uri": uri,
            "storage_type": "memory",
            "metadata": {
                "output_name": "return",
            },
        }
    ]


def pyplot_op(
    params: dict[str, Any], method_name: str, session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Execute a generic pyplot function."""
    if not hasattr(plt, method_name):
        raise ValueError(f"matplotlib.pyplot has no function {method_name}")

    method = getattr(plt, method_name)
    res = method(**params)

    if res is None:
        return []

    # If it returns a figure, we should handle it like figure() does
    if isinstance(res, plt.Figure):
        fig_id = str(uuid.uuid4())
        fig_uri = _build_obj_uri(session_id, env_id, fig_id)
        OBJECT_CACHE[fig_uri] = res
        res._mcp_ref_id = fig_id
        return [
            {
                "ref_id": fig_id,
                "type": "FigureRef",
                "python_class": "matplotlib.figure.Figure",
                "uri": fig_uri,
                "storage_type": "memory",
                "metadata": {
                    "output_name": "figure",
                    "figsize": res.get_size_inches().tolist(),
                    "dpi": int(res.get_dpi()),
                },
            }
        ]

    # For other returns, return as an ObjectRef so it can be inspected
    ref_id = str(uuid.uuid4())
    uri = _build_obj_uri(session_id, env_id, ref_id)
    OBJECT_CACHE[uri] = res
    return [
        {
            "ref_id": ref_id,
            "type": "ObjectRef",
            "python_class": f"{type(res).__module__}.{type(res).__name__}",
            "uri": uri,
            "storage_type": "memory",
            "metadata": {
                "output_name": "return",
            },
        }
    ]


def patch_op(
    params: dict[str, Any], class_name: str, session_id: str = "default", env_id: str = "base"
) -> list[dict]:
    """Create a patch from matplotlib.patches and store in cache."""
    if not hasattr(patches, class_name):
        raise ValueError(f"matplotlib.patches has no class {class_name}")

    cls = getattr(patches, class_name)
    patch = cls(**params)

    patch_id = str(uuid.uuid4())
    patch_uri = _build_obj_uri(session_id, env_id, patch_id)
    OBJECT_CACHE[patch_uri] = patch

    return [
        {
            "ref_id": patch_id,
            "type": "ObjectRef",
            "python_class": f"matplotlib.patches.{class_name}",
            "uri": patch_uri,
            "storage_type": "memory",
            "metadata": {"output_name": "output"},
        }
    ]


def set_xlabel(inputs: list[Any], params: dict[str, Any]) -> list[dict]:
    """Set the label for the x-axis."""
    return generic_op(inputs, params, "set_xlabel")


def set_ylabel(inputs: list[Any], params: dict[str, Any]) -> list[dict]:
    """Set the label for the y-axis."""
    return generic_op(inputs, params, "set_ylabel")


def set_title(inputs: list[Any], params: dict[str, Any]) -> list[dict]:
    """Set a title for the Axes."""
    return generic_op(inputs, params, "set_title")


def savefig(
    inputs: list[Any],
    params: dict[str, Any],
    work_dir: Path | None = None,
    session_id: str = "default",
    env_id: str = "base",
) -> list[dict]:
    """Save figure to file."""
    fig = None
    for name, value in inputs:
        if name == "figure":
            fig = _load_object(value)
            break
    if not fig and inputs:
        fig = _load_object(inputs[0][1])

    if not fig:
        raise ValueError("Missing 'figure' input for savefig")

    if work_dir is None:
        work_dir = Path(tempfile.gettempdir())
    work_dir.mkdir(parents=True, exist_ok=True)

    fmt = params.get("format", "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"

    out_path = work_dir / f"plot_{uuid.uuid4().hex}.{fmt}"

    dpi = params.get("dpi", fig.dpi)
    w_inch, h_inch = fig.get_size_inches()

    fig.savefig(str(out_path), **params)
    plt.close(fig)

    # Clean up OBJECT_CACHE (T045: Verify that figures are being closed after savefig)
    for uri, cached_fig in list(OBJECT_CACHE.items()):
        if cached_fig is fig:
            del OBJECT_CACHE[uri]

    plot_ref_fmt = "JPG" if fmt == "jpeg" else fmt.upper()

    return [
        {
            "type": "PlotRef",
            "format": plot_ref_fmt,
            "uri": out_path.absolute().as_uri(),
            "path": str(out_path.absolute()),
            "metadata": {
                "width_px": int(w_inch * dpi),
                "height_px": int(h_inch * dpi),
                "dpi": int(dpi),
                "plot_type": "matplotlib",
                "output_name": "plot",
            },
        }
    ]


def _find_axes(inputs: list[Any]) -> Any:
    """Helper to find axes in inputs."""
    for name, value in inputs:
        if name == "axes":
            return _load_object(value)
    if inputs:
        obj = _load_object(inputs[0][1])
        if hasattr(obj, "set_xlabel"):
            return obj
    raise ValueError("Missing 'axes' input")


def _load_object(artifact: Any) -> Any:
    """Load object from cache."""
    if isinstance(artifact, dict):
        uri = artifact.get("uri")
    else:
        uri = getattr(artifact, "uri", None)

    if uri and uri.startswith("obj://"):
        if uri not in OBJECT_CACHE:
            raise ValueError(f"Object with URI {uri} not found in memory cache")
        return OBJECT_CACHE[uri]
    return None


def _load_table(artifact: Any) -> pd.DataFrame:
    """Load DataFrame from artifact."""
    if isinstance(artifact, dict):
        uri = artifact.get("uri")
        path = artifact.get("path")
    else:
        uri = getattr(artifact, "uri", None)
        path = getattr(artifact, "path", None)

    if uri and uri.startswith("obj://"):
        if uri not in OBJECT_CACHE:
            raise ValueError(f"ObjectRef with URI '{uri}' not found in cache")
        obj = OBJECT_CACHE[uri]
        if isinstance(obj, pd.DataFrame):
            return obj
        return pd.DataFrame(obj)

    if not path and uri:
        parsed = urlparse(str(uri))
        path = unquote(parsed.path)
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]

    if not path:
        raise ValueError(f"Artifact missing URI or path: {artifact}")

    path_obj = Path(path)
    if path_obj.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _resolve_column_or_data(
    val: Any, df: pd.DataFrame | None, inputs: list[Any], params: dict[str, Any]
) -> Any:
    """Helper to resolve a value as either a column name in df or direct data."""
    if val is None:
        return None

    if isinstance(val, str) and df is not None and val in df.columns:
        return df[val].values

    return _resolve_data(val, inputs, params)


def _resolve_data(x_val: Any, inputs: list[tuple[str, Any]], params: dict[str, Any]) -> Any:
    """Resolve data for plotting."""
    if isinstance(x_val, str) and not x_val.startswith("obj://"):
        for _name, art in inputs:
            if isinstance(art, dict) and art.get("type") == "TableRef":
                df = _load_table(art)
                if x_val in df.columns:
                    return df[x_val].values

    if isinstance(x_val, dict) and "type" in x_val:
        if x_val["type"] == "TableRef":
            df = _load_table(x_val)
            return df.values
        elif x_val["type"] == "ObjectRef":
            return _load_object(x_val)
        elif x_val["type"] == "BioImageRef":
            img = BioImage(x_val.get("path"))
            return img.data.flatten()

    return x_val
