# Quick Start: Cellpose Object-Oriented API

## Prerequisites
- `bioimage-mcp` installed
- `bioimage-mcp-cellpose` environment created (`python -m bioimage_mcp doctor`)

## Example Usage

### Scenario 1: Fast Iterative Segmentation
In this scenario, we load the model once and reuse it for multiple images, which is much faster than reloading the weights for every call.

```python
# 1. Initialize the model (Constructor call)
# This returns an ObjectRef
model_ref = mcp.run(
    "cellpose.CellposeModel", 
    params={
        "model_type": "cyto3",
        "gpu": True
    }
)

# 2. Run segmentation on first image
# The function accepts an ObjectRef as the 'model' input
labels1 = mcp.run(
    "cellpose.CellposeModel.eval",
    inputs={
        "model": model_ref,
        "x": image1_ref
    },
    params={
        "channels": [0, 0],
        "diameter": 30
    }
)

# 3. Run segmentation on second image reusing the same model instance
labels2 = mcp.run(
    "cellpose.CellposeModel.eval",
    inputs={
        "model": model_ref,
        "x": image2_ref
    },
    params={
        "channels": [0, 0],
        "diameter": 30
    }
)

# 4. Clear model from GPU memory when done
mcp.run("evict", inputs={"ref": model_ref})
```

### Scenario 2: Model Fine-Tuning (Future P2)
```python
# Train a model and get the updated weights as an ObjectRef
new_model_ref = mcp.run(
    "cellpose.train",
    inputs={"train_data": dataset_ref},
    params={"n_epochs": 10}
)

# Use the fine-tuned model for inference
labels = mcp.run(
    "cellpose.CellposeModel.eval",
    inputs={
        "model": new_model_ref,
        "x": test_image_ref
    }
)
```
