from __future__ import annotations

from bioimage_mcp.registry.search import SearchIndex


def test_rank_prioritizes_match_count_then_score() -> None:
    index = SearchIndex()
    candidates = [
        {
            "fn_id": "base.phasor_calibrate",
            "name": "Phasor calibrate",
            "description": "Calibrate phasor coordinates",
            "tags": ["phasor", "calibration"],
        },
        {
            "fn_id": "base.phasor_from_flim",
            "name": "Phasor from FLIM",
            "description": "Compute phasor coordinates from FLIM",
            "tags": ["phasor", "flim"],
        },
    ]

    ranked = index.rank(keywords=["phasor", "calibrate"], candidates=candidates)

    assert [entry["fn_id"] for entry in ranked] == [
        "base.phasor_calibrate",
        "base.phasor_from_flim",
    ]
    assert ranked[0]["match_count"] > ranked[1]["match_count"]


def test_rank_breaks_ties_with_score() -> None:
    index = SearchIndex()
    candidates = [
        {
            "fn_id": "base.phasor_name",
            "name": "Phasor alignment",
            "description": "Alignment utilities",
            "tags": [],
        },
        {
            "fn_id": "base.phasor_tag",
            "name": "Alignment",
            "description": "Alignment utilities",
            "tags": ["phasor"],
        },
    ]

    ranked = index.rank(keywords=["phasor"], candidates=candidates)

    assert ranked[0]["fn_id"] == "base.phasor_name"
    assert ranked[0]["match_count"] == ranked[1]["match_count"] == 1
    assert ranked[0]["score"] > ranked[1]["score"]


def test_rank_is_typo_tolerant_with_ngrams() -> None:
    index = SearchIndex()
    candidates = [
        {
            "fn_id": "base.gaussian_blur",
            "name": "Gaussian blur",
            "description": "Blur an image",
            "tags": ["filter"],
        }
    ]

    ranked = index.rank(keywords=["gausian"], candidates=candidates)

    assert ranked, "Expected typo-tolerant match for 'gausian'"
    assert ranked[0]["fn_id"] == "base.gaussian_blur"
