from __future__ import annotations

import pytest
from bioimage_mcp.registry.dynamic.models import IOPattern
from bioimage_mcp.registry.loader import _map_io_pattern_to_ports


def test_map_phasor_to_scalar_ports() -> None:
    """Test that PHASOR_TO_SCALAR correctly maps to ports."""
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.PHASOR_TO_SCALAR)

    # inputs: two ports named "real" and "imag" with type "BioImageRef"
    assert len(inputs) == 2
    assert inputs[0].name == "real"
    assert inputs[0].artifact_type == "BioImageRef"
    assert inputs[1].name == "imag"
    assert inputs[1].artifact_type == "BioImageRef"

    # outputs: one port named "output" with type "BioImageRef"
    assert len(outputs) == 1
    assert outputs[0].name == "output"
    assert outputs[0].artifact_type == "BioImageRef"


def test_map_scalar_to_phasor_ports() -> None:
    """Test that SCALAR_TO_PHASOR correctly maps to ports."""
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.SCALAR_TO_PHASOR)

    # inputs: empty list
    assert len(inputs) == 0

    # outputs: two ports named "real" and "imag" with type "BioImageRef"
    assert len(outputs) == 2
    assert outputs[0].name == "real"
    assert outputs[0].artifact_type == "BioImageRef"
    assert outputs[1].name == "imag"
    assert outputs[1].artifact_type == "BioImageRef"


def test_map_phasor_to_other_ports() -> None:
    """Test that PHASOR_TO_OTHER correctly maps to ports."""
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.PHASOR_TO_OTHER)

    # inputs: two ports named "real" and "imag" with type "BioImageRef"
    assert len(inputs) == 2
    assert inputs[0].name == "real"
    assert inputs[0].artifact_type == "BioImageRef"
    assert inputs[1].name == "imag"
    assert inputs[1].artifact_type == "BioImageRef"

    # outputs: two ports named "real" and "imag" with type "BioImageRef"
    assert len(outputs) == 2
    assert outputs[0].name == "real"
    assert outputs[0].artifact_type == "BioImageRef"
    assert outputs[1].name == "imag"
    assert outputs[1].artifact_type == "BioImageRef"
