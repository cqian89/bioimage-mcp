from __future__ import annotations

import sqlite3

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def service():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    # Setup test data
    service.upsert_tool(
        tool_id="tools.base",
        name="Base Toolkit",
        description="Base image operations",
        tool_version="0.1.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/tools/base/manifest.yaml",
        available=True,
        installed=True,
    )

    # Gaussian Blur (filter, image in/out)
    service.upsert_function(
        fn_id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="Gaussian Blur",
        description="Apply Gaussian blur filter",
        tags=["filter", "blur"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "blurred", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )

    # Cellpose Segment (segmentation, image in, label out)
    service.upsert_function(
        fn_id="cellpose.models.CellposeModel.eval",
        tool_id="tools.cellpose",
        name="Cellpose Segment",
        description="Segment cells using Cellpose",
        tags=["segmentation", "cells"],
        inputs=[{"name": "x", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "labels", "artifact_type": "LabelImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"diameter": {"type": "number"}}},
    )

    yield service
    conn.close()


# T055: Search with query parameter
def test_search_with_query_returns_results(service):
    """Search with query should return ranked results."""
    result = service.search_functions(query="blur", limit=20, cursor=None)

    assert "results" in result
    assert len(result["results"]) > 0
    assert result["results"][0]["name"] == "Gaussian Blur"
    assert result["results"][0]["score"] > 0


# T056: Search with io_in/io_out filters
def test_search_with_io_filters(service):
    """Search should filter by input/output types."""
    # Filter for BioImageRef output
    result = service.search_functions(
        keywords="segment", io_out="LabelImageRef", limit=20, cursor=None
    )
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "cellpose.models.CellposeModel.eval"

    # Filter that should return nothing
    result = service.search_functions(
        keywords="blur", io_out="LabelImageRef", limit=20, cursor=None
    )
    assert len(result["results"]) == 0


# T057: Search with tags filter
def test_search_with_tags_filter(service):
    """Search should filter by tags."""
    result = service.search_functions(keywords="Gaussian", tags=["filter"], limit=20, cursor=None)
    assert len(result["results"]) == 1
    assert "filter" in result["results"][0]["tags"]

    result = service.search_functions(
        keywords="Gaussian", tags=["segmentation"], limit=20, cursor=None
    )
    assert len(result["results"]) == 0


# T058: Results include I/O summaries
def test_search_results_include_io_summaries(service):
    """Search results should include io.inputs and io.outputs."""
    result = service.search_functions(query="segment", limit=20, cursor=None)

    assert len(result["results"]) > 0
    fn = result["results"][0]
    assert "io" in fn
    assert "inputs" in fn["io"]
    assert "outputs" in fn["io"]

    # Check input structure
    assert fn["io"]["inputs"][0]["name"] == "x"
    assert fn["io"]["inputs"][0]["type"] == "BioImageRef"

    # Check output structure
    assert fn["io"]["outputs"][0]["name"] == "labels"
    assert fn["io"]["outputs"][0]["type"] == "LabelImageRef"


# T059: Validation error when NO criteria provided
def test_search_validation_failed_no_criteria(service):
    """Search should fail if no search criteria (query, keywords, io_in, io_out, tags) are provided."""
    result = service.search_functions(limit=20, cursor=None)
    assert "error" in result
    assert result["error"]["code"] == "VALIDATION_FAILED"
    assert "At least one search criterion required" in result["error"]["message"]


# T112: Validation error when BOTH query and keywords
def test_search_validation_failed_both_query_and_keywords(service):
    """Search should fail if both query and keywords provided."""
    result = service.search_functions(query="blur", keywords=["blur"], limit=20, cursor=None)
    assert "error" in result
    assert result["error"]["code"] == "VALIDATION_FAILED"
    assert "query and keywords are mutually exclusive" in result["error"]["message"]


# T113: Standalone filter search
def test_search_with_standalone_io_filter(service):
    """Search should work with only io_in or io_out filters."""
    # Search by io_out only
    result = service.search_functions(io_out="LabelImageRef", limit=20)
    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "cellpose.models.CellposeModel.eval"
    assert result["results"][0]["score"] == 0.0

    # Search by tags only
    result = service.search_functions(tags=["blur"], limit=20)
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "base.skimage.filters.gaussian"
