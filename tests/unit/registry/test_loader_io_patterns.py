from bioimage_mcp.registry.dynamic.models import IOPattern
from bioimage_mcp.registry.loader import _map_io_pattern_to_ports


def test_map_io_pattern_to_ports_new_patterns():
    # Test IMAGE_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.IMAGE_TO_JSON)
    assert len(inputs) == 1
    assert inputs[0].name == "image"
    assert inputs[0].artifact_type == "BioImageRef"
    assert len(outputs) == 1
    assert outputs[0].name == "output"
    assert outputs[0].artifact_type == "ScalarRef"

    # Test IMAGE_AND_LABELS_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.IMAGE_AND_LABELS_TO_JSON)
    assert len(inputs) == 2
    assert inputs[0].name == "image"
    assert inputs[1].name == "labels"
    assert inputs[1].artifact_type == "LabelImageRef"
    assert inputs[1].required is False
    assert len(outputs) == 1
    assert outputs[0].name == "output"
    assert outputs[0].artifact_type == "ScalarRef"

    # Test IMAGE_TO_LABELS_AND_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.IMAGE_TO_LABELS_AND_JSON)
    assert len(inputs) == 1
    assert inputs[0].name == "image"
    assert len(outputs) == 2
    assert outputs[0].name == "labels"
    assert outputs[0].artifact_type == "LabelImageRef"
    assert outputs[1].name == "output"
    assert outputs[1].artifact_type == "ScalarRef"


def test_map_io_pattern_to_ports_stats_patterns():
    # Test TABLE_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.TABLE_TO_JSON)
    assert len(inputs) == 1
    assert inputs[0].name == "table"
    assert inputs[0].artifact_type == "TableRef"
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "ScalarRef"

    # Test MULTI_TABLE_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.MULTI_TABLE_TO_JSON)
    assert len(inputs) == 1
    assert inputs[0].name == "tables"
    assert inputs[0].is_array is True
    assert "TableRef" in inputs[0].artifact_type
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "ScalarRef"

    # Test PARAMS_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.PARAMS_TO_JSON)
    assert len(inputs) == 0
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "ScalarRef"


def test_map_io_pattern_to_ports_spatial_patterns():
    # Test TABLE_TO_OBJECT
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.TABLE_TO_OBJECT)
    assert len(inputs) == 1
    assert inputs[0].name == "table"
    assert "TableRef" in inputs[0].artifact_type
    assert "ObjectRef" in inputs[0].artifact_type
    assert len(outputs) == 1
    assert outputs[0].name == "object"
    assert outputs[0].artifact_type == "ObjectRef"

    # Test OBJECT_AND_TABLE_TO_JSON
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.OBJECT_AND_TABLE_TO_JSON)
    assert len(inputs) == 2
    assert inputs[0].name == "object"
    assert inputs[0].artifact_type == "ObjectRef"
    assert inputs[1].name == "table"
    assert "TableRef" in inputs[1].artifact_type
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "ScalarRef"

    # Test TABLE_TO_FILE
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.TABLE_TO_FILE)
    assert len(inputs) == 1
    assert inputs[0].name == "table"
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "NativeOutputRef"

    # Test TABLE_PAIR_TO_FILE
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.TABLE_PAIR_TO_FILE)
    assert len(inputs) == 2
    assert inputs[0].name == "table_a"
    assert inputs[1].name == "table_b"
    assert len(outputs) == 1
    assert outputs[0].artifact_type == "NativeOutputRef"

    # Test ANY_TO_TABLE
    inputs, outputs = _map_io_pattern_to_ports(IOPattern.ANY_TO_TABLE)
    assert len(inputs) == 1
    assert inputs[0].name == "input"
    assert "TableRef" in inputs[0].artifact_type
    assert "BioImageRef" in inputs[0].artifact_type
    assert len(outputs) == 1
    assert outputs[0].name == "table"
    assert outputs[0].artifact_type == "TableRef"
