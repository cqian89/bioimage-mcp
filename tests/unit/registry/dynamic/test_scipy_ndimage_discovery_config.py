import sys

import yaml

from bioimage_mcp.registry.dynamic.adapters.scipy_ndimage import ScipyNdimageAdapter


def test_scipy_ndimage_discovery_config(tmp_path):
    # Create a dummy module
    module_dir = tmp_path / "dummy_scipy"
    module_dir.mkdir()
    (module_dir / "__init__.py").touch()

    module_content = """
def normal_fn(x):
    \"\"\"Normal function.\"\"\"
    return x

def deprecated_fn(x):
    \"\"\"Deprecated: this should be filtered out.
    
    Further description.
    \"\"\"
    return x

def sphinx_deprecated_fn(x):
    \"\"\"Another deprecated function.
    
    .. deprecated:: 1.0
    \"\"\"
    return x

def blacklisted_fn(x):
    \"\"\"Blacklisted function.\"\"\"
    return x
"""
    (module_dir / "ndimage.py").write_text(module_content)

    # Add to sys.path
    sys.path.insert(0, str(tmp_path))

    try:
        # Create blacklist file
        blacklist_file = tmp_path / "blacklist.yaml"
        blacklist_content = {"blacklist": ["blacklisted_fn", "non_existent_fn"]}
        with open(blacklist_file, "w") as f:
            yaml.dump(blacklist_content, f)

        # Create a dummy manifest path
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.touch()

        adapter = ScipyNdimageAdapter()
        config = {
            "modules": ["dummy_scipy.ndimage"],
            "blacklist_path": "blacklist.yaml",
            "_manifest_path": str(manifest_path),
        }

        results = adapter.discover(config)

        fn_names = [r.fn_id.split(".")[-1] for r in results]

        assert "normal_fn" in fn_names
        assert "deprecated_fn" not in fn_names
        assert "sphinx_deprecated_fn" not in fn_names
        assert "blacklisted_fn" not in fn_names

        # Verify it works without blacklist too
        config_no_bl = {"modules": ["dummy_scipy.ndimage"], "_manifest_path": str(manifest_path)}
        results_no_bl = adapter.discover(config_no_bl)
        fn_names_no_bl = [r.fn_id.split(".")[-1] for r in results_no_bl]
        assert "blacklisted_fn" in fn_names_no_bl

    finally:
        sys.path.pop(0)
        if "dummy_scipy" in sys.modules:
            del sys.modules["dummy_scipy"]
        if "dummy_scipy.ndimage" in sys.modules:
            del sys.modules["dummy_scipy.ndimage"]
