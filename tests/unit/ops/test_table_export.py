from pathlib import Path

import pandas as pd
import pytest
from bioimage_mcp_base.ops.io import PathNotAllowedError, table_export


@pytest.fixture
def sample_df():
    return pd.DataFrame({"id": [1, 2, 3], "value": [1.23456789012345, 2.0, 3.14159265358979]})


@pytest.fixture
def table_ref(sample_df, tmp_path):
    csv_path = tmp_path / "input.csv"
    sample_df.to_csv(csv_path, index=False)
    return {
        "ref_id": "test_table",
        "type": "TableRef",
        "uri": f"file://{csv_path}",
        "path": str(csv_path),
        "format": "csv",
        "columns": list(sample_df.columns),
        "row_count": len(sample_df),
        "delimiter": ",",
    }


def test_table_export_csv(table_ref, tmp_path, monkeypatch):
    dest_path = tmp_path / "output.csv"
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", f'["{str(tmp_path.resolve())}"]')
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", f'["{str(tmp_path.resolve())}"]')

    result = table_export(
        inputs={"data": table_ref},
        params={"dest_path": str(dest_path), "sep": ","},
        work_dir=tmp_path,
    )

    assert dest_path.exists()
    df_loaded = pd.read_csv(dest_path)
    assert len(df_loaded) == 3
    assert list(df_loaded.columns) == ["id", "value"]

    # Check precision
    assert df_loaded.loc[2, "value"] == pytest.approx(3.14159265358979, abs=1e-14)

    # Check output ref
    out_ref = result["outputs"]["table"]
    assert out_ref["type"] == "TableRef"
    assert out_ref["format"] == "csv"
    assert out_ref["delimiter"] == ","
    assert out_ref["row_count"] == 3


def test_table_export_tsv(table_ref, tmp_path, monkeypatch):
    dest_path = tmp_path / "output.tsv"
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", f'["{str(tmp_path.resolve())}"]')
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", f'["{str(tmp_path.resolve())}"]')

    result = table_export(
        inputs={"data": table_ref},
        params={"dest_path": str(dest_path), "sep": "\t"},
        work_dir=tmp_path,
    )

    assert dest_path.exists()
    df_loaded = pd.read_csv(dest_path, sep="\t")
    assert len(df_loaded) == 3
    out_ref = result["outputs"]["table"]
    assert out_ref["format"] == "tsv"
    assert out_ref["delimiter"] == "\t"


def test_table_export_denied(table_ref, tmp_path, monkeypatch):
    dest_path = Path("/forbidden/output.csv")
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", "[]")

    with pytest.raises(PathNotAllowedError):
        table_export(
            inputs={"data": table_ref}, params={"dest_path": str(dest_path)}, work_dir=tmp_path
        )


def test_table_export_object_ref(sample_df, tmp_path, monkeypatch):
    # Mock object cache
    from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

    obj_id = "test_obj"
    OBJECT_CACHE[obj_id] = sample_df

    obj_ref = {
        "ref_id": obj_id,
        "type": "ObjectRef",
        "uri": f"obj://session/env/{obj_id}",
        "python_class": "pandas.DataFrame",
        "storage_type": "memory",
    }

    dest_path = tmp_path / "output_obj.csv"
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", f'["{str(tmp_path.resolve())}"]')

    try:
        result = table_export(
            inputs={"data": obj_ref}, params={"dest_path": str(dest_path)}, work_dir=tmp_path
        )

        assert dest_path.exists()
        df_loaded = pd.read_csv(dest_path)
        assert len(df_loaded) == len(sample_df)
    finally:
        if obj_id in OBJECT_CACHE:
            del OBJECT_CACHE[obj_id]
