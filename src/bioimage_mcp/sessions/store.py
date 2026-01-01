from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, cast

from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.models import Session, SessionStep
from bioimage_mcp.storage import sqlite


class SessionStore:
    def __init__(self, config: Config | None = None) -> None:
        if config:
            self.conn = sqlite.connect(config)
        else:
            # In-memory DB for testing or default usage
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row
            sqlite.init_schema(self.conn)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def create_session(self, session_id: str, connection_hint: str | None = None) -> Session:
        # Explicitly provide fields to satisfy linter
        now = datetime.now(timezone.utc).isoformat()
        session = Session(
            session_id=session_id,
            connection_hint=connection_hint,
            created_at=cast(Any, now),
            last_activity_at=cast(Any, now),
            status="active",
        )
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO sessions (
                    session_id, created_at, last_activity_at, status, connection_hint
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.created_at,
                    session.last_activity_at,
                    session.status,
                    session.connection_hint,
                ),
            )
        return session

    def get_session(self, session_id: str) -> Session:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"Session {session_id} not found")

        # Pydantic model expects fields matching the Row columns
        # Row factory is sqlite3.Row, so it behaves like a dict
        return Session(**dict(row))

    def update_activity(self, session_id: str, last_activity_at: datetime | None = None) -> Session:
        # First ensure session exists
        self.get_session(session_id)

        if last_activity_at:
            new_activity = last_activity_at.isoformat()
        else:
            new_activity = datetime.now(timezone.utc).isoformat()

        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET last_activity_at = ? WHERE session_id = ?",
                (new_activity, session_id),
            )

        return self.get_session(session_id)

    def add_step_attempt(
        self,
        session_id: str,
        step_id: str,
        ordinal: int,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        status: str = "running",
        started_at: datetime | str | None = None,
        ended_at: datetime | str | None = None,
        run_id: str | None = None,
        outputs: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        log_ref_id: str | None = None,
        canonical: bool = True,
    ) -> SessionStep:
        # Check session exists
        self.get_session(session_id)

        # Normalize timestamps
        if isinstance(started_at, datetime):
            started_at_str = started_at.isoformat()
        elif started_at is None:
            started_at_str = datetime.now(timezone.utc).isoformat()
        else:
            started_at_str = started_at

        if isinstance(ended_at, datetime):
            ended_at_str = ended_at.isoformat()
        else:
            ended_at_str = ended_at

        # Construct model first to leverage defaults if needed (though we're passing most args)
        # Note: input/output dicts need serialization for DB, but model keeps them as dicts.
        # using cast to bypass strange linter errors regarding datetime/str mismatch
        step = SessionStep(
            session_id=session_id,
            step_id=step_id,
            ordinal=ordinal,
            fn_id=fn_id,
            inputs=inputs,
            params=params,
            status=cast(Any, status),
            started_at=cast(Any, started_at_str),
            ended_at=cast(Any, ended_at_str),
            run_id=run_id,
            outputs=outputs,
            error=error,
            log_ref_id=log_ref_id,
            canonical=canonical,
        )

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO session_steps (
                    step_id, session_id, ordinal, fn_id, inputs_json, params_json,
                    status, started_at, ended_at, run_id, error_json, outputs_json,
                    log_ref_id, canonical
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step.step_id,
                    step.session_id,
                    step.ordinal,
                    step.fn_id,
                    json.dumps(step.inputs),
                    json.dumps(step.params),
                    step.status,
                    step.started_at,
                    step.ended_at,
                    step.run_id,
                    json.dumps(step.error) if step.error else None,
                    json.dumps(step.outputs) if step.outputs else None,
                    step.log_ref_id,
                    1 if step.canonical else 0,
                ),
            )
        return step

    def list_step_attempts(self, session_id: str) -> list[SessionStep]:
        # Check session exists
        self.get_session(session_id)

        rows = self.conn.execute(
            "SELECT * FROM session_steps WHERE session_id = ? ORDER BY ordinal, started_at",
            (session_id,),
        ).fetchall()

        steps = []
        for row in rows:
            data = dict(row)
            # Deserialize JSON fields
            data["inputs"] = json.loads(data["inputs_json"])
            data["params"] = json.loads(data["params_json"])
            data["outputs"] = json.loads(data["outputs_json"]) if data["outputs_json"] else None
            data["error"] = json.loads(data["error_json"]) if data["error_json"] else None
            data["canonical"] = bool(data["canonical"])

            # Remove _json keys
            del data["inputs_json"]
            del data["params_json"]
            del data["outputs_json"]
            del data["error_json"]

            steps.append(SessionStep(**data))

        return steps

    def set_canonical(self, session_id: str, step_id: str, ordinal: int) -> None:
        # Check session exists
        self.get_session(session_id)

        with self.conn:
            # Set all steps at this ordinal for this session to non-canonical
            self.conn.execute(
                """
                UPDATE session_steps 
                SET canonical = 0 
                WHERE session_id = ? AND ordinal = ?
                """,
                (session_id, ordinal),
            )
            # Set the specific step to canonical
            self.conn.execute(
                """
                UPDATE session_steps 
                SET canonical = 1 
                WHERE session_id = ? AND step_id = ?
                """,
                (session_id, step_id),
            )

    def get_active_functions(self, session_id: str) -> list[str]:
        # Check session exists
        self.get_session(session_id)

        rows = self.conn.execute(
            "SELECT fn_id FROM session_active_functions WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return [row["fn_id"] for row in rows]

    def replace_active_functions(self, session_id: str, fn_ids: list[str]) -> list[str]:
        # Check session exists
        self.get_session(session_id)

        with self.conn:
            self.conn.execute(
                "DELETE FROM session_active_functions WHERE session_id = ?",
                (session_id,),
            )
            if fn_ids:
                self.conn.executemany(
                    "INSERT INTO session_active_functions (session_id, fn_id) VALUES (?, ?)",
                    [(session_id, fn_id) for fn_id in fn_ids],
                )

        return self.get_active_functions(session_id)

    def update_session_status(self, session_id: str, status: str) -> None:
        # Check session exists
        self.get_session(session_id)

        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?",
                (status, session_id),
            )
