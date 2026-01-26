import pytest
from bioimage_mcp.registry.dynamic.adapters.scipy import ScipyAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


@pytest.mark.requires_base
def test_scipy_spatial_adapter_discovers():
    adapter = ScipyAdapter()
    # Test composite discovery
    config = {"modules": ["scipy.ndimage", "scipy.spatial", "scipy.spatial.distance"]}
    fns = adapter.discover(config)

    fn_ids = [f.fn_id for f in fns]
    assert "scipy.spatial.distance.cdist" in fn_ids
    assert "scipy.spatial.Voronoi" in fn_ids
    assert "scipy.spatial.Delaunay" in fn_ids

    cdist = next(f for f in fns if f.fn_id == "scipy.spatial.distance.cdist")
    assert cdist.io_pattern == IOPattern.TABLE_PAIR_TO_FILE
    assert "metric" in cdist.parameters
    assert "columns_a" in cdist.parameters
    assert "vi_strategy" in cdist.parameters

    voronoi = next(f for f in fns if f.fn_id == "scipy.spatial.Voronoi")
    assert voronoi.io_pattern == IOPattern.TABLE_TO_JSON
    assert "columns" in voronoi.parameters


@pytest.mark.requires_base
def test_scipy_spatial_adapter_isolation():
    adapter = ScipyAdapter()
    # Test only spatial discovery
    config = {"modules": ["scipy.spatial"]}
    fns = adapter.discover(config)

    fn_ids = [f.fn_id for f in fns]
    assert "scipy.spatial.Voronoi" in fn_ids
    assert "scipy.spatial.Delaunay" in fn_ids
    # cdist is in scipy.spatial.distance sub-module, but we handle it if scipy.spatial is in modules?
    # Actually my discover implementation checks:
    # if "scipy.spatial" not in modules and "scipy.spatial.distance" not in modules:
    #     return super().discover(module_config)
    # So if "scipy.spatial" is in modules, it should return all 3.
    assert "scipy.spatial.distance.cdist" in fn_ids
