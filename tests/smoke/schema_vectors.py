from __future__ import annotations

from typing import Any

# Curated list of function IDs to validate per environment/toolset
# Focuses on: property names, types, defaults, required fields, enums.
# Ignores: description, title, examples.
SCHEMA_VECTORS: dict[str, dict[str, Any]] = {
    "base.io.bioimage.load": {
        "inputs": {},
        "outputs": {"image": {"type": "BioImageRef"}},
        "params_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "format": {"type": "string"}},
            "required": ["path"],
        },
    },
    "cellpose.models.CellposeModel.eval": {
        "inputs": {
            "model": {"type": "ObjectRef", "required": True},
            "x": {"type": "BioImageRef", "required": True},
        },
        "outputs": {"labels": {"type": "LabelImageRef"}},
        "params_schema": {
            "type": "object",
            "properties": {
                "anisotropy": {"type": "string"},
                "augment": {"type": "boolean"},
                "batch_size": {"type": "integer"},
                "bsize": {"type": "integer"},
                "cellprob_threshold": {"type": "number"},
                "channel_axis": {"type": "string"},
                "channels": {"type": "array", "items": {"type": "integer"}},
                "compute_masks": {"type": "boolean"},
                "diameter": {"type": "string"},
                "do_3D": {"type": "boolean"},
                "flow3D_smooth": {"type": "integer"},
                "flow_threshold": {"type": "number"},
                "interp": {"type": "boolean"},
                "invert": {"type": "boolean"},
                "max_size_fraction": {"type": "number"},
                "min_size": {"type": "integer"},
                "niter": {"type": "string"},
                "normalize": {"type": "boolean"},
                "progress": {"type": "string"},
                "resample": {"type": "boolean"},
                "rescale": {"type": "string"},
                "stitch_threshold": {"type": "number"},
                "tile_overlap": {"type": "number"},
                "z_axis": {"type": "string"},
            },
            "required": [],
        },
    },
}
