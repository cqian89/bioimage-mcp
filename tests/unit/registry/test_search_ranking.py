from __future__ import annotations

from bioimage_mcp.registry.search import SearchIndex


def test_rank_prioritizes_match_count_then_score() -> None:
    index = SearchIndex()
    candidates = [
        {
            "id": "base.phasorpy.phasor.phasor_transform",
            "name": "Phasor calibrate",
            "description": "Calibrate phasor coordinates",
            "tags": ["phasor", "calibration"],
        },
        {
            "id": "base.phasorpy.phasor.phasor_from_signal",
            "name": "Phasor from FLIM",
            "description": "Compute phasor coordinates from FLIM",
            "tags": ["phasor", "flim"],
        },
    ]

    ranked = index.rank(keywords=["phasor", "calibrate"], candidates=candidates)

    assert [entry["id"] for entry in ranked] == [
        "base.phasorpy.phasor.phasor_transform",
        "base.phasorpy.phasor.phasor_from_signal",
    ]
    assert ranked[0]["match_count"] > ranked[1]["match_count"]


def test_rank_breaks_ties_with_score() -> None:
    index = SearchIndex()
    candidates = [
        {
            "id": "base.phasor_name",
            "name": "Phasor alignment",
            "description": "Alignment utilities",
            "tags": [],
        },
        {
            "id": "base.phasor_tag",
            "name": "Alignment",
            "description": "Alignment utilities",
            "tags": ["phasor"],
        },
    ]

    ranked = index.rank(keywords=["phasor"], candidates=candidates)

    assert ranked[0]["id"] == "base.phasor_name"
    assert ranked[0]["match_count"] == ranked[1]["match_count"] == 1
    assert ranked[0]["score"] > ranked[1]["score"]


def test_rank_is_typo_tolerant_with_ngrams() -> None:
    index = SearchIndex()
    candidates = [
        {
            "id": "base.gaussian_blur",
            "name": "Gaussian blur",
            "description": "Blur an image",
            "tags": ["filter"],
        }
    ]

    ranked = index.rank(keywords=["gausian"], candidates=candidates)

    assert ranked, "Expected typo-tolerant match for 'gausian'"
    assert ranked[0]["id"] == "base.gaussian_blur"


def test_rank_accepts_fn_id_alias() -> None:
    index = SearchIndex()
    candidates = [
        {
            "fn_id": "base.gaussian_blur",
            "name": "Gaussian blur",
            "description": "Blur an image",
            "tags": ["filter"],
        }
    ]

    ranked = index.rank(keywords=["gaussian"], candidates=candidates)

    assert ranked[0]["id"] == "base.gaussian_blur"
    assert "fn_id" not in ranked[0]
