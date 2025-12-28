from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, Optional


def _now() -> str:
    """SQLite-friendly UTC timestamp."""
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RunStoreV2:
    """
    Minimal v2 run store for Phase D.3:
    - persists runs_v2 row
    - persists run_state_v2 blob
    - supports get/put state used by GraphTickV2
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory

    def create_run_v2(
        self,
        env: str,
        lane: str,
        mode: str,
        job_type: str,
        requested_by: str,
        run_graph: Dict[str, Any],
        params: Dict[str, Any],
        parent_run_id: Optional[str] = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        created_at = _now()

        state: Dict[str, Any] = {
            "schema_version": "v2",
            "run_id": run_id,
            "env": env,
            "lane": lane,
            "mode": mode,
            "job_type": job_type,
            "status": "queued",
            "created_at": created_at,
            "started_at": None,
            "finished_at": None,
            "last_error": None,
            "run_graph": run_graph,
            "step_states": {},
            "artifacts": {},
        }

        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO runs_v2 (
                    run_id,
                    schema_version,
                    status,
                    env,
                    lane,
                    mode,
                    job_type,
                    requested_by,
                    parent_run_id,
                    created_at,
                    run_graph_json,
                    params_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "v2",
                    "queued",
                    env,
                    lane,
                    mode,
                    job_type,
                    requested_by,
                    parent_run_id,
                    created_at,
                    json.dumps(run_graph),
                    json.dumps(params),
                ),
            )
            cur.execute(
                """
                INSERT INTO run_state_v2 (run_id, state_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (run_id, json.dumps(state), created_at),
            )
            con.commit()

        return run_id

    def get_run_state_v2(self, run_id: str) -> Dict[str, Any]:
        with self.sf() as con:
            cur = con.cursor()
            cur.execute("SELECT state_json FROM run_state_v2 WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                raise KeyError(f"run_state_v2 missing run_id={run_id}")
            return json.loads(row[0])

    def put_run_state_v2(self, run_id: str, state: Dict[str, Any]) -> None:
        """Update run_state_v2 blob and summary columns on runs_v2."""
        updated_at = _now()
        status = state.get("status", "queued")
        started_at = state.get("started_at")
        finished_at = state.get("finished_at")
        last_error = state.get("last_error")

        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE run_state_v2
                SET state_json = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (json.dumps(state), updated_at, run_id),
            )
            cur.execute(
                """
                UPDATE runs_v2
                SET
                    status = ?,
                    started_at = COALESCE(started_at, ?),
                    finished_at = ?,
                    last_error_json = ?
                WHERE run_id = ?
                """,
                (
                    status,
                    started_at,
                    finished_at,
                    json.dumps(last_error) if last_error is not None else None,
                    run_id,
                ),
            )
            con.commit()
