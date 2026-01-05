# Quickstart: MCP Interface Redesign

**Feature**: 016-mcp-interface-redesign  
**Date**: 2026-01-05

## Overview

This guide shows how to use the redesigned 8-tool MCP surface for BioImage-MCP.

## Tool Summary

| Tool | Purpose | Key Features |
|------|---------|--------------|
| `list` | Browse catalog hierarchy | Child counts, I/O summaries |
| `describe` | Get full details for any node | Separated inputs/outputs/params_schema |
| `search` | Find functions by criteria | Query, tags, I/O type filters |
| `run` | Execute a function | Single execution, session support |
| `status` | Poll execution status | Progress tracking |
| `artifact_info` | Get artifact metadata | Text preview for logs |
| `session_export` | Export workflow record | External inputs tracking |
| `session_replay` | Replay on new data | Parameter overrides |

---

## Example Workflow: Discover → Describe → Run

### Step 1: List available environments

```json
// Request
{"path": null, "limit": 10, "include_counts": true}

// Response
{
  "items": [
    {
      "id": "base",
      "type": "environment",
      "name": "base",
      "summary": "Base image processing tools",
      "children": {"total": 3, "by_type": {"package": 3}}
    },
    {
      "id": "cellpose",
      "type": "environment",
      "name": "cellpose",
      "summary": "Cell segmentation tools",
      "children": {"total": 1, "by_type": {"package": 1}}
    }
  ]
}
```

### Step 2: Browse to filters module

```json
// Request
{"path": "base.skimage.filters", "include_counts": true}

// Response
{
  "items": [
    {
      "id": "base.skimage.filters.gaussian",
      "type": "function",
      "name": "gaussian",
      "summary": "Apply Gaussian filter to reduce noise",
      "io": {
        "inputs": [{"name": "image", "type": "BioImageRef", "required": true}],
        "outputs": [{"name": "output", "type": "BioImageRef"}]
      }
    }
  ],
  "expanded_from": "base.skimage.filters"
}
```

### Step 3: Describe the function

```json
// Request
{"id": "base.skimage.filters.gaussian"}

// Response
{
  "id": "base.skimage.filters.gaussian",
  "type": "function",
  "summary": "Apply a Gaussian filter to an image to reduce noise and detail.",
  "tags": ["denoise", "smooth", "filter"],
  "inputs": {
    "image": {
      "type": "BioImageRef",
      "required": true,
      "hints": {"expected_axes": ["Y", "X"], "min_ndim": 2}
    }
  },
  "outputs": {
    "output": {"type": "BioImageRef"}
  },
  "params_schema": {
    "type": "object",
    "properties": {
      "sigma": {"type": "number", "default": 1.0},
      "preserve_range": {"type": "boolean", "default": false}
    }
  },
  "examples": [
    {"inputs": {"image": "<BioImageRef>"}, "params": {"sigma": 1.5}}
  ]
}
```

### Step 4: Run the function

```json
// Request
{
  "id": "base.skimage.filters.gaussian",
  "inputs": {"image": "ref_abc123"},
  "params": {"sigma": 1.5}
}

// Response
{
  "session_id": "session_xyz",
  "run_id": "run_456",
  "status": "success",
  "id": "base.skimage.filters.gaussian",
  "outputs": {
    "output": {
      "ref_id": "ref_def789",
      "type": "BioImageRef",
      "uri": "file:///artifacts/ref_def789.ome.tiff",
      "dims": ["Y", "X"],
      "ndim": 2,
      "dtype": "uint16",
      "shape": [1024, 1024],
      "size_bytes": 2097152
    }
  }
}
```

---

## Example: Search for Segmentation Tools

```json
// Request
{
  "query": "segment",
  "io_out": "LabelImageRef",
  "limit": 5
}

// Response
{
  "results": [
    {
      "id": "cellpose.eval",
      "type": "function",
      "name": "Cellpose Eval",
      "summary": "Cell segmentation using Cellpose models",
      "tags": ["segmentation", "deep-learning"],
      "io": {
        "inputs": [{"name": "image", "type": "BioImageRef", "required": true}],
        "outputs": [{"name": "labels", "type": "LabelImageRef"}]
      },
      "score": 44.3
    }
  ]
}
```

---

## Example: Dry-Run Validation

Validate a call before execution:

```json
// Request
{
  "id": "base.skimage.filters.gaussian",
  "inputs": {},  // Missing required input!
  "params": {"sigma": 1.0},
  "dry_run": true
}

// Response
{
  "session_id": "session_xyz",
  "run_id": "run_dry_001",
  "status": "validation_failed",
  "id": "base.skimage.filters.gaussian",
  "outputs": {},
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Missing required input 'image'",
    "details": [
      {
        "path": "/inputs/image",
        "expected": "BioImageRef",
        "actual": "missing",
        "hint": "Provide a BioImageRef from a prior tool output or import"
      }
    ]
  }
}
```

---

## Example: Session Export and Replay

### Export a session

```json
// Request (after running multiple tools in session_xyz)
{"session_id": "session_xyz"}

// Response
{
  "session_id": "session_xyz",
  "workflow_ref": {
    "ref_id": "workflow_abc",
    "type": "TableRef",
    "format": "workflow-record-json",
    "uri": "file:///artifacts/workflow_abc.json"
  }
}
```

### Replay on new data

```json
// Request
{
  "workflow_ref": {"ref_id": "workflow_abc", "type": "TableRef"},
  "inputs": {
    "raw_image": "ref_new_image_001"  // New input data
  },
  "params_overrides": {
    "base.skimage.filters.gaussian": {"sigma": 2.0}  // Adjust parameter
  }
}

// Response
{
  "run_id": "run_replay_001",
  "session_id": "session_replay_xyz",
  "status": "running",
  "workflow_ref": {"ref_id": "workflow_new_abc", "type": "TableRef"}
}
```

---

## Error Handling

All tools return structured errors on failure:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Function 'invalid.function.id' not found",
    "details": [
      {
        "path": "/id",
        "expected": "valid function ID",
        "actual": "invalid.function.id",
        "hint": "Use 'search' or 'list' to find valid function IDs"
      }
    ]
  }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `VALIDATION_FAILED` | Request validation error |
| `NOT_FOUND` | Catalog node or artifact not found |
| `EXECUTION_FAILED` | Tool execution error |
| `PERMISSION_DENIED` | Filesystem access denied |
| `SCHEMA_MISMATCH` | Workflow record incompatibility |

---

## Key Differences from Previous API

1. **8 tools instead of 13**: Simplified, consistent surface
2. **Child counts**: `list` returns `children.total` and `children.by_type`
3. **Separated ports/params**: `describe` returns `inputs`, `outputs`, `params_schema` separately
4. **Single execution tool**: `run` replaces both `run_function` and `run_workflow`
5. **Workflow replay**: New `session_replay` enables running workflows on new data
6. **Structured errors**: JSON Pointer paths and actionable hints on all errors
