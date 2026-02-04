"""
Marker enforcement tests for equivalence tests.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest


def get_markers(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, list[Any]]]:
    markers = []
    for decorator in node.decorator_list:
        marker_name = None
        args = []

        # Handle @pytest.mark.name
        if isinstance(decorator, ast.Attribute):
            if isinstance(decorator.value, ast.Attribute) and decorator.value.attr == "mark":
                marker_name = decorator.attr

        # Handle @pytest.mark.name(...)
        elif isinstance(decorator, ast.Call):
            func = decorator.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "mark"
            ):
                marker_name = func.attr
                for arg in decorator.args:
                    if isinstance(arg, ast.Constant):
                        args.append(arg.value)
                    elif isinstance(arg, ast.Str):  # For older python versions if needed
                        args.append(arg.s)

        if marker_name:
            markers.append((marker_name, args))
    return markers


@pytest.mark.smoke_minimal
def test_equivalence_markers_enforcement():
    """
    Ensure all test_equivalence_*.py tests follow marker conventions (FR-009).

    Rules:
    - Must have EXACTLY ONE of: @pytest.mark.smoke_pr OR @pytest.mark.smoke_extended.
    - Must have @pytest.mark.requires_env("bioimage-mcp-...")
    - Must have exactly one of: @pytest.mark.uses_minimal_data OR @pytest.mark.requires_lfs_dataset
    - Must NOT have @pytest.mark.smoke_minimal
    """
    smoke_dir = Path(__file__).parent
    equivalence_files = list(smoke_dir.glob("test_equivalence_*.py"))

    assert equivalence_files, "No test_equivalence_*.py files found!"

    errors = []

    for test_file in equivalence_files:
        with open(test_file, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(test_file))

        # First pass: find class-level markers
        class_markers: dict[str, list[tuple[str, list[Any]]]] = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_markers[node.name] = get_markers(node)

        # Second pass: find functions and check their markers (including inherited)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                check_test_node(test_file.name, node, [], errors)
            elif isinstance(node, ast.ClassDef):
                parent_markers = class_markers.get(node.name, [])
                for subnode in node.body:
                    if isinstance(
                        subnode, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and subnode.name.startswith("test_"):
                        check_test_node(
                            f"{test_file.name}::{node.name}", subnode, parent_markers, errors
                        )

    if errors:
        pytest.fail("Marker enforcement failed:\n" + "\n".join(errors))


def check_test_node(
    context: str,
    node: ast.FunctionDef,
    parent_markers: list[tuple[str, list[Any]]],
    errors: list[str],
):
    local_markers = get_markers(node)
    all_markers = parent_markers + local_markers
    marker_names = [m[0] for m in all_markers]

    test_id = f"{context}:{node.name}"

    # 1. smoke_pr XOR smoke_extended
    tier_markers = {"smoke_pr", "smoke_extended"}
    present_tier_markers = tier_markers.intersection(set(marker_names))
    if len(present_tier_markers) != 1:
        errors.append(
            f"{test_id} must have exactly one of {tier_markers}, found: {present_tier_markers}"
        )

    # 2. smoke_minimal (should NOT be present)
    if "smoke_minimal" in marker_names:
        errors.append(f"{test_id} should NOT have @pytest.mark.smoke_minimal")

    # 3. requires_env
    env_markers = [m for m in all_markers if m[0] == "requires_env"]
    # Also support convenience markers as valid env declarations for now
    convenience_markers = {"requires_stardist", "requires_cellpose", "requires_base"}
    has_convenience = convenience_markers.intersection(set(marker_names))

    if not env_markers and not has_convenience:
        errors.append(f"{test_id} missing @pytest.mark.requires_env(...)")
    elif env_markers:
        valid_env = False
        for _, args in env_markers:
            if args and any(isinstance(a, str) and a.startswith("bioimage-mcp-") for a in args):
                valid_env = True
                break
        if not valid_env:
            errors.append(f"{test_id} @pytest.mark.requires_env must specify a bioimage-mcp-* env")

    # 4. Dataset markers
    dataset_markers = {"uses_minimal_data", "requires_lfs_dataset"}
    present_dataset_markers = dataset_markers.intersection(set(marker_names))
    if len(present_dataset_markers) != 1:
        msg = (
            f"{test_id} must have exactly one of {dataset_markers}, "
            f"found: {present_dataset_markers}"
        )
        errors.append(msg)
