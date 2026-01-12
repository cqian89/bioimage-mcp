MATPLOTLIB_DENYLIST = {
    "show",
    "pause",
    "ginput",
    "connect",
    "waitforbuttonpress",
    "ion",
    "ioff",
}

MATPLOTLIB_PYPLOT_ALLOWLIST = {
    "figure": {
        "summary": "Create a new figure, or activate an existing figure.",
        "io_pattern": "PURE_CONSTRUCTOR",
        "params": {
            "num": {"type": "integer", "description": "Unique identifier for the figure."},
            "figsize": {"type": "array", "description": "[width, height] in inches"},
            "dpi": {"type": "number", "description": "Dots per inch"},
            "facecolor": {"type": "string", "description": "The figure patch facecolor"},
            "edgecolor": {"type": "string", "description": "The figure patch edge color"},
            "frameon": {
                "type": "boolean",
                "description": "Whether to draw the figure frame",
                "default": True,
            },
            "clear": {
                "type": "boolean",
                "description": "If True and the figure already exists, then it is cleared",
                "default": False,
            },
        },
    },
    "subplots": {
        "summary": "Create a figure and a set of subplots.",
        "io_pattern": "MATPLOTLIB_SUBPLOTS",
        "params": {
            "nrows": {"type": "integer", "default": 1},
            "ncols": {"type": "integer", "default": 1},
            "sharex": {
                "type": "string",
                "description": "Controls sharing of properties among x-axes",
            },
            "sharey": {
                "type": "string",
                "description": "Controls sharing of properties among y-axes",
            },
            "squeeze": {"type": "boolean", "default": True},
            "figsize": {"type": "array", "description": "[width, height] in inches"},
        },
    },
    "close": {
        "summary": "Close a figure window.",
        "io_pattern": "OBJECTREF_CHAIN",
    },
}

MATPLOTLIB_FIGURE_ALLOWLIST = {
    "savefig": {
        "summary": "Save the current figure.",
        "io_pattern": "PLOT",
        "params": {
            "format": {
                "type": "string",
                "description": "The file format (e.g. 'png', 'pdf', 'svg')",
            },
            "dpi": {"type": "number", "description": "The resolution in dots per inch"},
            "bbox_inches": {
                "type": "string",
                "description": "Bounding box in inches: 'tight' or None",
            },
            "transparent": {
                "type": "boolean",
                "description": "Whether to make the background transparent",
                "default": False,
            },
        },
    },
    "add_subplot": {
        "summary": "Add an Axes to the figure as part of a subplot arrangement.",
        "io_pattern": "OBJECTREF_CHAIN",
    },
    "tight_layout": {
        "summary": "Adjust the padding between and around subplots.",
        "io_pattern": "OBJECTREF_CHAIN",
    },
    "suptitle": {
        "summary": "Add a centered title to the figure.",
        "io_pattern": "OBJECTREF_CHAIN",
    },
}

MATPLOTLIB_AXES_ALLOWLIST = {
    "imshow": {
        "summary": "Display data as an image, i.e., on a 2D regular raster.",
        "io_pattern": "MATPLOTLIB_AXES_OP",
        "params": {
            "X": {"type": "object", "description": "Image data (BioImageRef or array)"},
            "cmap": {"type": "string", "description": "Colormap"},
            "aspect": {"type": "string", "description": "Aspect ratio"},
            "interpolation": {"type": "string", "description": "Interpolation method"},
            "alpha": {"type": "number", "description": "Transparency"},
            "vmin": {"type": "number", "description": "Minimum data value"},
            "vmax": {"type": "number", "description": "Maximum data value"},
            "origin": {
                "type": "string",
                "description": "Place the [0, 0] index of the array in the upper left or lower left",
            },
            "max_display_size": {
                "type": "integer",
                "description": "Maximum size for display downsampling",
            },
        },
    },
    "plot": {
        "summary": "Plot y versus x as lines and/or markers.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "x": {"type": "array", "description": "x-coordinates"},
            "y": {"type": "array", "description": "y-coordinates"},
            "fmt": {"type": "string", "description": "Format string (e.g. 'ro' for red circles)"},
            "label": {"type": "string", "description": "Label for legend"},
            "linewidth": {"type": "number", "description": "Line width"},
            "color": {"type": "string", "description": "Line color"},
        },
    },
    "scatter": {
        "summary": "A scatter plot of y vs. x with varying marker size and/or color.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "x": {"type": "array", "description": "x-coordinates"},
            "y": {"type": "array", "description": "y-coordinates"},
            "s": {"type": "number", "description": "Marker size"},
            "c": {"type": "string", "description": "Marker color"},
            "marker": {"type": "string", "description": "Marker style"},
            "cmap": {"type": "string", "description": "Colormap"},
            "alpha": {"type": "number", "description": "Transparency"},
        },
    },
    "hist": {
        "summary": "Compute and plot a histogram.",
        "io_pattern": "MATPLOTLIB_AXES_OP",
        "params": {
            "x": {"type": "array", "description": "Input values"},
            "bins": {"type": "integer", "description": "Number of histogram bins"},
            "range": {"type": "array", "description": "The lower and upper range of the bins"},
            "density": {
                "type": "boolean",
                "description": "Whether to normalize the histogram",
                "default": False,
            },
            "color": {"type": "string", "description": "Bar color"},
            "alpha": {"type": "number", "description": "Transparency"},
        },
    },
    "set_title": {
        "summary": "Set a title for the Axes.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "label": {"type": "string", "description": "The title text"},
            "fontdict": {
                "type": "object",
                "description": "A dictionary controlling the appearance of the title text",
            },
            "loc": {
                "type": "string",
                "description": "Which title to set: 'center', 'left', 'right'",
            },
        },
    },
    "set_xlabel": {
        "summary": "Set the label for the x-axis.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "xlabel": {"type": "string", "description": "The label text"},
        },
    },
    "set_ylabel": {
        "summary": "Set the label for the y-axis.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "ylabel": {"type": "string", "description": "The label text"},
        },
    },
    "set_xlim": {
        "summary": "Set the x-axis view limits.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "left": {"type": "number", "description": "The left xlim"},
            "right": {"type": "number", "description": "The right xlim"},
        },
    },
    "set_ylim": {
        "summary": "Set the y-axis view limits.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "bottom": {"type": "number", "description": "The bottom ylim"},
            "top": {"type": "number", "description": "The top ylim"},
        },
    },
    "grid": {
        "summary": "Configure the grid lines.",
        "io_pattern": "OBJECTREF_CHAIN",
        "params": {
            "visible": {"type": "boolean", "description": "Whether to show the grid lines"},
            "which": {
                "type": "string",
                "description": "The grid lines to apply the changes on: 'major', 'minor', 'both'",
            },
            "axis": {
                "type": "string",
                "description": "The axis to apply the changes on: 'both', 'x', 'y'",
            },
        },
    },
    "add_patch": {
        "summary": "Add a Patch to the Axes; return the patch.",
        "io_pattern": "MATPLOTLIB_AXES_OP",
        "params": {
            "p": {"type": "object", "description": "The patch to add"},
        },
    },
    "colorbar": {
        "summary": "Add a colorbar to a plot.",
        "io_pattern": "OBJECTREF_CHAIN",
    },
}

MATPLOTLIB_PATCHES_ALLOWLIST = {
    "Circle": {
        "summary": "A circle patch.",
        "io_pattern": "PURE_CONSTRUCTOR",
        "params": {
            "xy": {"type": "array", "description": "(x, y) center of the circle"},
            "radius": {"type": "number", "description": "Radius of the circle"},
            "color": {"type": "string", "description": "Patch color"},
            "fill": {
                "type": "boolean",
                "description": "Whether to fill the circle",
                "default": True,
            },
            "alpha": {"type": "number", "description": "Transparency"},
        },
    },
    "Rectangle": {
        "summary": "A rectangle patch.",
        "io_pattern": "PURE_CONSTRUCTOR",
        "params": {
            "xy": {"type": "array", "description": "(x, y) lower-left corner"},
            "width": {"type": "number", "description": "Rectangle width"},
            "height": {"type": "number", "description": "Rectangle height"},
            "angle": {"type": "number", "description": "Rotation angle in degrees"},
            "color": {"type": "string", "description": "Patch color"},
            "fill": {
                "type": "boolean",
                "description": "Whether to fill the rectangle",
                "default": True,
            },
        },
    },
}
