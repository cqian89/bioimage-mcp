import pytest
from bioimage_mcp.registry.dynamic.adapters.scipy import ScipyAdapter
from bioimage_mcp.registry.dynamic.adapters.scipy_stats import ScipyStatsAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


@pytest.mark.requires_base
def test_scipy_stats_adapter_discovers_wrappers():
    """ScipyStatsAdapter should discover curated stats wrappers."""
    adapter = ScipyStatsAdapter()
    module_config = {"modules": ["scipy.stats"]}

    discovered = adapter.discover(module_config)
    fn_ids = [fn.fn_id for fn in discovered]

    # 1. Summary stats
    assert "scipy.stats.describe_table" in fn_ids
    assert "scipy.stats.mean_table" in fn_ids
    assert "scipy.stats.skew_table" in fn_ids
    assert "scipy.stats.kurtosis_table" in fn_ids

    # 2. Test wrappers
    assert "scipy.stats.ttest_1samp_table" in fn_ids
    assert "scipy.stats.ttest_ind_table" in fn_ids
    assert "scipy.stats.ttest_rel_table" in fn_ids
    assert "scipy.stats.f_oneway_table" in fn_ids
    assert "scipy.stats.ks_2samp_table" in fn_ids


@pytest.mark.requires_base
def test_scipy_stats_adapter_discovers_distributions():
    """ScipyStatsAdapter should discover curated distributions."""
    adapter = ScipyStatsAdapter()
    module_config = {"modules": ["scipy.stats"]}

    discovered = adapter.discover(module_config)
    fn_ids = [fn.fn_id for fn in discovered]

    # Continuous representative
    assert "scipy.stats.norm.cdf" in fn_ids
    assert "scipy.stats.norm.pdf" in fn_ids
    assert "scipy.stats.norm.ppf" in fn_ids

    # Discrete representative
    assert "scipy.stats.poisson.pmf" in fn_ids
    assert "scipy.stats.poisson.cdf" in fn_ids
    assert "scipy.stats.poisson.ppf" in fn_ids


@pytest.mark.requires_base
def test_scipy_stats_adapter_io_patterns():
    """ScipyStatsAdapter should assign correct IO patterns."""
    adapter = ScipyStatsAdapter()
    module_config = {"modules": ["scipy.stats"]}

    discovered = {fn.fn_id: fn for fn in adapter.discover(module_config)}

    # TABLE_TO_JSON
    assert discovered["scipy.stats.mean_table"].io_pattern == IOPattern.TABLE_TO_JSON
    assert discovered["scipy.stats.ttest_1samp_table"].io_pattern == IOPattern.TABLE_TO_JSON

    # TABLE_PAIR_TO_JSON
    assert discovered["scipy.stats.ttest_ind_table"].io_pattern == IOPattern.TABLE_PAIR_TO_JSON
    assert discovered["scipy.stats.ks_2samp_table"].io_pattern == IOPattern.TABLE_PAIR_TO_JSON

    # MULTI_TABLE_TO_JSON
    assert discovered["scipy.stats.f_oneway_table"].io_pattern == IOPattern.MULTI_TABLE_TO_JSON

    # PARAMS_TO_JSON
    assert discovered["scipy.stats.norm.cdf"].io_pattern == IOPattern.PARAMS_TO_JSON


@pytest.mark.requires_base
def test_scipy_composite_adapter_discovery_delegation():
    """ScipyAdapter should delegate discovery to sub-adapters."""
    adapter = ScipyAdapter()
    # Note: ScipyAdapter uses "modules" list
    module_config = {"modules": ["scipy.ndimage", "scipy.stats"]}

    discovered = adapter.discover(module_config)
    fn_ids = [fn.fn_id for fn in discovered]

    # From ndimage (representative)
    assert "scipy.ndimage.sobel" in fn_ids

    # From stats (representative)
    assert "scipy.stats.ttest_ind_table" in fn_ids
    assert "scipy.stats.norm.cdf" in fn_ids
