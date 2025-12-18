from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


class RunStore:
    def __init__(self, config: Config, *, conn: sqlite3.Connection | None = None):
        self._config = config
        self._conn = conn or connect(config)

    def create_run(
        self,
        *,
        workflow_spec: dict,
        inputs: dict,
        params: dict,
        provenance: dict,
        log_ref_id: str,
    ):
        run_id = uuid.uuid4().hex
        created_at = _now()

        self._conn.execute(
            """
            INSERT INTO runs(
                run_id,
                status,
                created_at,
                started_at,
                ended_at,
                workflow_spec_json,
                inputs_json,
                params_json,
                outputs_json,
                log_ref_id,
                error_json,
                provenance_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "queued",
                created_at,
                None,
                None,
                json.dumps(workflow_spec),
                json.dumps(inputs),
                json.dumps(params),
                None,
                log_ref_id,
                None,
                json.dumps(provenance),
            ),
        )
        self._conn.commit()

        from bioimage_mcp.runs.models import Run

        return Run(
            run_id=run_id,
            status="queued",
            created_at=created_at,
            workflow_spec=workflow_spec,
            inputs=inputs,
            params=params,
            outputs=None,
            log_ref_id=log_ref_id,
            error=None,
            provenance=provenance,
        )

    def set_status(
        self, run_id: str, status: str, *, outputs: dict | None = None, error: dict | None = None
    ) -> None:
        started_at = _now() if status == "running" else None
        ended_at = _now() if status in {"succeeded", "failed", "cancelled"} else None

        self._conn.execute(
            """
            UPDATE runs
            SET status = ?,
                started_at = COALESCE(started_at, ?),
                ended_at = COALESCE(ended_at, ?),
                outputs_json = COALESCE(outputs_json, ?),
                error_json = COALESCE(error_json, ?)
            WHERE run_id = ?
            """,
            (
                status,
                started_at,
                ended_at,
                json.dumps(outputs) if outputs is not None else None,
                json.dumps(error) if error is not None else None,
                run_id,
            ),
        )
        self._conn.commit()

    def get(self, run_id: str):
        row = self._conn.execute(
            "SELECT run_id, status, created_at, started_at, ended_at, "
            "workflow_spec_json, inputs_json, params_json, outputs_json, "
            "log_ref_id, error_json, provenance_json "
            "FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)

        from bioimage_mcp.runs.models import Run

        return Run(
            run_id=row["run_id"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            workflow_spec=json.loads(row["workflow_spec_json"]),
            inputs=json.loads(row["inputs_json"]),
            params=json.loads(row["params_json"]),
            outputs=json.loads(row["outputs_json"]) if row["outputs_json"] else None,
            log_ref_id=row["log_ref_id"],
            error=json.loads(row["error_json"]) if row["error_json"] else None,
            provenance=json.loads(row["provenance_json"]),
        )
