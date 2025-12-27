from __future__ import annotations

from bioimage_mcp.registry.dynamic.models import IOPattern
from bioimage_mcp.registry.loader import _map_io_pattern_to_ports


def test_labels_to_table_ports_include_intensity_image() -> None:
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.LABELS_TO_TABLE)

    assert [port.name for port in inputs] == ["labels", "intensity_image"]
    assert inputs[0].required is True
    assert inputs[1].required is False
    assert outputs[0].name == "table"
