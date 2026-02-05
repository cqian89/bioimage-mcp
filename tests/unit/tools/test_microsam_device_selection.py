import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def load_device_module():
    module_path = (
        Path(__file__).parent.parent.parent.parent
        / "tools"
        / "microsam"
        / "bioimage_mcp_microsam"
        / "device.py"
    )
    spec = importlib.util.spec_from_file_location("bioimage_mcp_microsam.device", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def device_module():
    return load_device_module()


@pytest.fixture
def mock_torch():
    torch = MagicMock()
    torch.cuda = MagicMock()
    torch.backends = MagicMock()
    torch.backends.mps = MagicMock()
    return torch


def test_select_device_auto_prefers_cuda(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = True
    mock_torch.backends.mps.is_available.return_value = True

    selected = device_module.select_device("auto", torch_module=mock_torch)
    assert selected == "cuda"


def test_select_device_auto_falls_back_to_mps(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = True

    selected = device_module.select_device("auto", torch_module=mock_torch)
    assert selected == "mps"


def test_select_device_auto_falls_back_to_cpu(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    selected = device_module.select_device("auto", torch_module=mock_torch)
    assert selected == "cpu"


def test_select_device_forced_cuda_available(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = True

    selected = device_module.select_device("cuda", torch_module=mock_torch)
    assert selected == "cuda"


def test_select_device_forced_cuda_unavailable_raises(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = False

    with pytest.raises(RuntimeError, match="Requested device 'cuda' is not available"):
        device_module.select_device("cuda", torch_module=mock_torch, strict=True)


def test_select_device_forced_mps_unavailable_raises(device_module, mock_torch):
    mock_torch.backends.mps.is_available.return_value = False

    with pytest.raises(RuntimeError, match="Requested device 'mps' is not available"):
        device_module.select_device("mps", torch_module=mock_torch, strict=True)


def test_select_device_forced_cuda_not_strict(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = False

    # Should NOT raise when strict=False
    selected = device_module.select_device("cuda", torch_module=mock_torch, strict=False)
    assert selected == "cuda"


def test_select_device_invalid_preference(device_module, mock_torch):
    with pytest.raises(ValueError, match="Invalid device preference"):
        device_module.select_device("invalid", torch_module=mock_torch)


def test_select_device_mps_missing_backend(device_module, mock_torch):
    mock_torch.cuda.is_available.return_value = False
    # Simulate missing backends.mps attribute
    del mock_torch.backends.mps

    selected = device_module.select_device("auto", torch_module=mock_torch)
    assert selected == "cpu"
