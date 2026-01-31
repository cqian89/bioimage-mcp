# Phase 15 Context: Enhance artifact_info with Multimodal Previews and ObjectRef Type Visibility

## Phase Overview

**Goal:** Extend artifact_info to support image previews for multimodal LLMs, table row previews, and improved ObjectRef type identification.

**Scope:** This phase enhances the `artifact_info` API endpoint to return richer preview data that LLMs can consume directly.

---

## Image Preview Output

### Format & Structure
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Image format | PNG | Lossless, universal browser/LLM support |
| Default size | 256×256 max dimension | Balance of detail and token efficiency |
| Response structure | Nested `image_preview` object | `{base64, format, width, height}` |
| Aspect ratio | Preserve | No distortion, variable output dimensions |

### Request Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `include_image_preview` | bool | Explicit opt-in to generate image preview |
| `image_preview_size` | int | Max dimension override (default: 256) |
| `channels` | int or list[int] | Which channel(s) to render (e.g., `0` or `[0,1,2]`) |

### Label Image Handling
| Decision | Choice |
|----------|--------|
| Colormap | Auto-apply `tab20` (cycles for >20 labels) |
| Additional metadata | Include region count + centroids in response |

### Multi-channel Images
- Caller specifies which channel(s) via `channels` parameter
- No default projection across channels — explicit selection required

### Failure Handling
- Silently omit `image_preview` field if generation fails
- Caller checks for field presence (no error object, no request failure)

---

## Dimensionality Reduction

### Projection Methods
All five methods supported: `max`, `mean`, `sum`, `min`, `slice`

| Decision | Choice |
|----------|--------|
| Default projection | Max projection |
| Parameter name | `projection` (string or dict) |
| Per-axis control | Supported: `projection={"Z": "max", "T": "slice"}` |

### Axis Reduction Order
- Preset order: Reduce Z first, then T
- Channel axis (C) handled separately via `channels` parameter

### Slice Selection
| Parameter | Type | Description |
|-----------|------|-------------|
| `slice_indices` | dict | Per-axis indices, e.g., `{"Z": 10, "T": 0}` |

If using `projection="slice"` and index not specified, behavior TBD by implementation (suggest: middle index fallback).

### Already 2D Images
- Skip projection logic entirely
- Preview generated directly from 2D data

---

## Table Row Previews

### Defaults
| Setting | Value |
|---------|-------|
| Default row count | 5 rows |
| Format | Markdown table |
| Types | Separate `dtypes` field in metadata |

### Request Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `preview_rows` | int | Number of rows to include (default: 5) |
| `preview_columns` | int | Max columns to include (caller-specified) |

### Response Structure
```json
{
  "table_preview": "| col1 | col2 |\n|------|------|\n| a | 1 |",
  "dtypes": {"col1": "object", "col2": "int64"},
  "total_rows": 1000,
  "total_columns": 50
}
```

---

## ObjectRef Type Visibility

### native_type Field
| Decision | Choice |
|----------|--------|
| Content | Fully qualified class name (e.g., `cellpose.models.Cellpose`) |
| Multiple types | Union string format: `"TypeA | TypeB"` |

### params_schema Integration
| Decision | Choice |
|----------|--------|
| Placement | Inline on parameter: `"x-native-type": "module.Class"` |
| Description | Also enrich description with type context |

Example:
```json
{
  "model": {
    "type": "string",
    "description": "Expects a Cellpose model object",
    "x-native-type": "cellpose.models.Cellpose"
  }
}
```

### ObjectRef Preview
| Decision | Choice |
|----------|--------|
| Preview content | `repr()` string when available |
| Length limit | 500 chars, truncate with `...` |

### Accessibility
| Decision | Choice |
|----------|--------|
| Scope | Session-scoped (in-memory within session only) |
| Invalid access error | `OBJECT_REF_EXPIRED` specific error code |

---

## Deferred Ideas

*None captured during this discussion.*

---

## Implementation Notes

### New artifact_info Parameters (Summary)
```
include_image_preview: bool       # opt-in for image preview
image_preview_size: int           # max dimension (default: 256)
channels: int | list[int]         # channel selection for multi-channel images
projection: str | dict            # "max" or {"Z": "max", "T": "slice"}
slice_indices: dict               # {"Z": 10} for slice projections
preview_rows: int                 # table row count (default: 5)
preview_columns: int              # max columns for wide tables
```

### Response Additions
- `image_preview`: `{base64, format, width, height}` — omitted on failure
- `image_preview.region_count`, `image_preview.centroids` — for LabelImageRef only
- `table_preview`: Markdown string
- `dtypes`: Column type mapping
- `native_type`: Fully qualified class name (ObjectRef)
- `object_preview`: repr() string (ObjectRef)

---

*Context captured: 2026-01-31*
