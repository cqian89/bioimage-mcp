from __future__ import annotations
from __future__ import annotations

import pathlib

import griffe
from pydantic import BaseModel, Field


class StaticParameter(BaseModel):
    name: str
    annotation: str | None = None
    default: str | None = None


class StaticCallable(BaseModel):
    name: str
    qualified_name: str
    docstring: str | None = None
    parameters: list[StaticParameter] = Field(default_factory=list)
    source: str | None = None


class StaticModuleReport(BaseModel):
    module_name: str
    callables: list[StaticCallable] = Field(default_factory=list)


def inspect_module(module: str, search_paths: list[pathlib.Path]) -> StaticModuleReport:
    """Uses griffe to load module/package WITHOUT importing tool code.

    Extracts fully qualified module path(s) and callable definitions.
    """
    loader = griffe.GriffeLoader(search_paths=[str(p) for p in search_paths])
    griffe_mod = loader.load(module)

    callables = []
    # all_members includes members of the module and its submodules if it's a package
    for member in griffe_mod.all_members.values():
        if member.kind is not griffe.Kind.FUNCTION:
            continue

        try:
            params = []
            for p in member.parameters:
                params.append(
                    StaticParameter(
                        name=p.name,
                        annotation=str(p.annotation) if p.annotation else None,
                        default=str(p.default) if p.default else None,
                    )
                )
            docstring = member.docstring.value if member.docstring else None
            source = member.source
        except (griffe.AliasResolutionError, griffe.CyclicAliasError):
            continue

        callables.append(
            StaticCallable(
                name=member.name,
                qualified_name=member.path,
                docstring=docstring,
                parameters=params,
                source=source,
            )
        )

    return StaticModuleReport(module_name=module, callables=callables)
