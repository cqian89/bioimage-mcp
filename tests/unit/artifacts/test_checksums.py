from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.checksums import sha256_file, sha256_tree


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("hello")

    digest1 = sha256_file(path)
    digest2 = sha256_file(path)

    assert digest1 == digest2
    assert len(digest1) == 64


def test_sha256_tree_changes_with_contents(tmp_path: Path) -> None:
    root = tmp_path / "dir"
    (root / "sub").mkdir(parents=True)

    (root / "sub" / "a.txt").write_text("a")
    digest1 = sha256_tree(root)

    (root / "sub" / "a.txt").write_text("b")
    digest2 = sha256_tree(root)

    assert digest1 != digest2
    assert len(digest1) == 64
