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

### Scenario 2: Model Fine-Tuning
Train a model on specific data and then use the resulting weights for inference.

```python
# 1. Train or fine-tune a model
# This returns a NativeOutputRef for the weights and a TableRef for losses
train_results = mcp.run(
    "cellpose.train_seg",
    inputs={
        "image": train_image_ref,
        "mask": train_label_ref
    },
    params={
        "n_epochs": 10,
        "model_type": "cyto3"
    }
)
weights_ref = train_results.outputs["weights"]

# 2. Initialize a model using the newly trained weights
# We pass the weights ref to the 'pretrained_model' parameter
model_ref = mcp.run(
    "cellpose.CellposeModel",
    params={
        "pretrained_model": weights_ref,
        "gpu": True
    }
)

# 3. Use the fine-tuned model for inference
labels = mcp.run(
    "cellpose.CellposeModel.eval",
    inputs={
        "model": model_ref,
        "x": test_image_ref
    }
)
```

### Resource Management

#### Evicting individual objects
To free up memory for a specific model:
```python
mcp.run("evict", inputs={"ref": model_ref})
```

#### Clearing the entire cache
To clear all models and objects from the tool's memory:
```python
mcp.run("cellpose.cache.clear")
```
