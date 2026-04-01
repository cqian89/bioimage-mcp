from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FILES_REQUIRING_POINTER_GUARDS = [
    "tests/unit/base/test_bioimage_loading.py",
    "tests/unit/base/test_bioimage_lazy_loading.py",
    "tests/unit/api/test_metadata_extraction.py",
    "tests/unit/registry/dynamic/test_phasorpy_adapter.py",
    "tests/contract/test_artifact_metadata_contract.py",
    "tests/smoke/test_equivalence_trackpy.py",
    "tests/smoke/test_trackpy_e2e.py",
    "tests/smoke/test_flim_phasor_live.py",
]


def test_lfs_backed_tests_use_pointer_skip_helper() -> None:
    for relative_path in FILES_REQUIRING_POINTER_GUARDS:
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "skip_if_lfs_pointer(" in content, (
            f"{relative_path} must skip cleanly when an LFS pointer is present"
        )
