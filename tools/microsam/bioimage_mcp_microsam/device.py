from __future__ import annotations

from typing import Any


def select_device(device: str, *, torch_module: Any = None, strict: bool = True) -> str:
    """Select the best available device based on preference and availability.

    Args:
        device: One of "auto", "cuda", "mps", "cpu".
        torch_module: Optional torch module stub for testing.
        strict: If True, raise error if forced accelerator is unavailable.

    Returns:
        The selected device string ("cuda", "mps", or "cpu").
    """
    valid_devices = ("auto", "cuda", "mps", "cpu")
    if device not in valid_devices:
        raise ValueError(f"Invalid device preference: '{device}'. Must be one of {valid_devices}")

    if torch_module is None:
        import torch

        torch_module = torch

    if device == "auto":
        # Preference: CUDA > MPS > CPU
        if torch_module.cuda.is_available():
            return "cuda"

        # Check for MPS (resilient to missing attributes)
        if hasattr(torch_module, "backends") and hasattr(torch_module.backends, "mps"):
            if torch_module.backends.mps.is_available():
                return "mps"

        return "cpu"

    if device == "cpu":
        return "cpu"

    # Forced accelerator (cuda or mps)
    is_available = False
    if device == "cuda":
        is_available = torch_module.cuda.is_available()
    elif device == "mps":
        if hasattr(torch_module, "backends") and hasattr(torch_module.backends, "mps"):
            is_available = torch_module.backends.mps.is_available()

    if not is_available and strict:
        selection_order = "CUDA > MPS > CPU"
        raise RuntimeError(
            f"Requested device '{device}' is not available on this system. "
            f"(Selection order: {selection_order})"
        )

    return device
