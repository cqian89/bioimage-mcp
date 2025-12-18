from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtocolRequest:
    fn_id: str
    params: dict
    inputs: dict
    work_dir: str


@dataclass(frozen=True)
class ProtocolResponse:
    ok: bool
    outputs: dict
    log: str
    error: dict | None = None
